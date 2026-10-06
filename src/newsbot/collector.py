from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from telethon import TelegramClient, events, utils
from telethon.tl.types import MessageService

from newsbot.branches import materialize_branches
from newsbot.config import Config, Donor
from newsbot.db import Database
from newsbot.pipeline import Pipeline, PostInput
from newsbot.review_queue import ReviewQueue

logger = logging.getLogger(__name__)


@dataclass
class Piece:
    donor: str
    message_id: int
    text: str
    photo: bytes | None
    grouped_id: int | None
    signature_template: str | None
    branch: str = "Новости"
    publish_channel: str = ""
    review_channel: str = ""


class Collector:
    """Listen to configured public channels only. Never walks dialogs."""

    def __init__(
        self,
        client: TelegramClient,
        config: Config,
        db: Database,
        pipeline: Pipeline,
        review: ReviewQueue,
    ) -> None:
        self.client = client
        self.config = config
        self.db = db
        self.pipeline = pipeline
        self.review = review
        self._by_peer: dict[int, list[tuple[str, Donor, str, str]]] = {}
        self._albums: dict[tuple[str, str, int], list[Piece]] = {}
        self._tasks: dict[tuple[str, str, int], asyncio.Task[None]] = {}
        self._listening = False

    async def reload(self) -> None:
        """Subscribe to the donors of every branch after a config change."""
        if self._listening:
            self.client.remove_event_handler(self._on_message)
            self._listening = False
        await self.start()

    async def start(self) -> None:
        self._by_peer.clear()
        entities: dict[str, object] = {}
        chats = []
        for branch in materialize_branches(self.config):
            for donor in branch.donors:
                if not donor.enabled:
                    continue
                key = donor.username.casefold()
                entity = entities.get(key)
                if entity is None:
                    try:
                        entity = await self.client.get_entity(donor.username)
                    except Exception as exc:
                        message = f"@{donor.username}: {exc.__class__.__name__}"
                        logger.error("donor resolve failed: %s", message)
                        self.db.add_error("donor", message)
                        continue
                    if not getattr(entity, "broadcast", False):
                        message = f"@{donor.username}: не канал, пропуск"
                        logger.error(message)
                        self.db.add_error("donor", message)
                        continue
                    entities[key] = entity
                    chats.append(entity)
                    logger.info("donor ready @%s", donor.username)
                peer_id = utils.get_peer_id(entity)
                self._by_peer.setdefault(peer_id, []).append(
                    (branch.name, donor, branch.publish_channel, branch.review_channel)
                )
        if not chats:
            logger.warning("нет доступных каналов-доноров, чтение не запущено")
            return
        self.client.add_event_handler(self._on_message, events.NewMessage(chats=chats))
        self._listening = True

    async def stop(self) -> None:
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        self._albums.clear()

    async def _on_message(self, event: events.NewMessage.Event) -> None:
        try:
            await self._handle(event)
        except Exception as exc:
            logger.exception("collector failed")
            self.db.add_error("collector", exc.__class__.__name__)

    async def _handle(self, event: events.NewMessage.Event) -> None:
        bindings = self._by_peer.get(event.chat_id) or []
        if not bindings:
            return
        message = event.message
        photo: bytes | None | object = ...
        for branch_name, donor, publish_channel, review_channel in bindings:
            seen_key = f"{branch_name}:{donor.username}"
            if self.db.is_paused():
                self.db.mark_seen(seen_key, message.id)
                logger.info("paused, skip @%s #%s", donor.username, message.id)
                continue
            if not self.db.mark_seen(seen_key, message.id):
                continue
            if isinstance(message, MessageService) or getattr(message, "action", None):
                self.db.log_publish(
                    donor=donor.username,
                    source_message_ids=[message.id],
                    target_message_ids=None,
                    fingerprint="",
                    status="skip",
                    reason="service",
                )
                continue
            if photo is ...:
                photo = await self._download_photo(donor.username, message)
            piece = Piece(
                donor=donor.username,
                message_id=message.id,
                text=message.message or "",
                photo=photo if isinstance(photo, bytes) else None,
                grouped_id=message.grouped_id,
                signature_template=donor.signature,
                branch=branch_name,
                publish_channel=publish_channel,
                review_channel=review_channel,
            )
            if message.grouped_id:
                await self._buffer(piece)
                continue
            await self._process([piece])

    async def _download_photo(self, donor: str, message: object) -> bytes | None:
        if not getattr(message, "photo", None):
            return None
        try:
            blob = await self.client.download_media(message, file=bytes)
        except Exception as exc:
            self.db.add_error("download", f"@{donor}: {exc.__class__.__name__}")
            return None
        if isinstance(blob, bytes) and blob:
            return blob
        return None

    async def _buffer(self, piece: Piece) -> None:
        assert piece.grouped_id is not None
        key = (piece.branch, piece.donor, piece.grouped_id)
        self._albums.setdefault(key, []).append(piece)
        if key not in self._tasks:
            self._tasks[key] = asyncio.create_task(self._flush(key))

    async def _flush(self, key: tuple[str, str, int]) -> None:
        try:
            await asyncio.sleep(self.config.publish.album_flush_seconds)
            pieces = self._albums.pop(key, [])
            if pieces:
                await self._process(pieces)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("album flush failed")
            self.db.add_error("collector", exc.__class__.__name__)
        finally:
            self._tasks.pop(key, None)

    async def _process(self, pieces: list[Piece]) -> None:
        ordered = sorted(pieces, key=lambda item: item.message_id)
        primary = max(ordered, key=lambda item: len(item.text or ""))
        photos = [item.photo for item in ordered if item.photo]
        photos = photos[: self.config.publish.album_max_items]
        result = await self.pipeline.run(
            PostInput(
                donor=primary.donor,
                message_id=primary.message_id,
                text=primary.text,
                is_service=False,
                has_photo=bool(photos),
                footer=self._footer(primary.branch),
            ),
            record=False,
        )
        source_ids = [item.message_id for item in ordered]
        if result.action != "publish":
            self.db.log_publish(
                donor=primary.donor,
                source_message_ids=source_ids,
                target_message_ids=None,
                fingerprint=result.fingerprint,
                status=result.action,
                reason=result.reason,
            )
            logger.info(
                "not queued @%s %s: %s",
                primary.donor,
                ",".join(str(item) for item in source_ids),
                result.reason,
            )
            return
        preview_id = await self.review.submit(
            donor=primary.donor,
            source_ids=source_ids,
            text=result.text,
            photos=[blob for blob in photos if blob is not None],
            dedupe_text=result.dedupe_text,
            branch_name=primary.branch,
            publish_channel=primary.publish_channel,
            review_channel=primary.review_channel,
        )
        if preview_id is None:
            return
        self.db.log_publish(
            donor=primary.donor,
            source_message_ids=source_ids,
            target_message_ids=None,
            fingerprint=result.fingerprint,
            status="review",
            reason=f"preview {preview_id}",
        )

    def _footer(self, branch_name: str) -> str:
        for branch in materialize_branches(self.config):
            if branch.name == branch_name:
                return branch.template
        return ""
