from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from telethon import TelegramClient, events, utils
from telethon.tl.types import MessageService

from newsbot.config import Config, Donor
from newsbot.db import Database
from newsbot.pipeline import Pipeline, PostInput
from newsbot.publisher import Outgoing, Publisher

logger = logging.getLogger(__name__)


@dataclass
class Piece:
    donor: str
    message_id: int
    text: str
    photo: bytes | None
    grouped_id: int | None
    signature_template: str | None


class Collector:
    """Listen to configured public channels only. Never walks dialogs."""

    def __init__(
        self,
        client: TelegramClient,
        config: Config,
        db: Database,
        pipeline: Pipeline,
        publisher: Publisher,
    ) -> None:
        self.client = client
        self.config = config
        self.db = db
        self.pipeline = pipeline
        self.publisher = publisher
        self._by_peer: dict[int, Donor] = {}
        self._albums: dict[tuple[str, int], list[Piece]] = {}
        self._tasks: dict[tuple[str, int], asyncio.Task[None]] = {}
        self._listening = False

    async def start(self) -> None:
        chats = []
        for donor in self.config.donors:
            if not donor.enabled:
                continue
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
            peer_id = utils.get_peer_id(entity)
            self._by_peer[peer_id] = donor
            chats.append(entity)
            logger.info("donor ready @%s", donor.username)
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
        donor = self._by_peer.get(event.chat_id)
        if donor is None:
            return
        message = event.message
        if self.db.is_paused():
            self.db.mark_seen(donor.username, message.id)
            logger.info("paused, skip @%s #%s", donor.username, message.id)
            return
        if not self.db.mark_seen(donor.username, message.id):
            return
        if isinstance(message, MessageService) or getattr(message, "action", None):
            self.db.log_publish(
                donor=donor.username,
                source_message_ids=[message.id],
                target_message_ids=None,
                fingerprint="",
                status="skip",
                reason="service",
            )
            return
        photo = await self._download_photo(donor.username, message)
        piece = Piece(
            donor=donor.username,
            message_id=message.id,
            text=message.message or "",
            photo=photo,
            grouped_id=message.grouped_id,
            signature_template=donor.signature,
        )
        if message.grouped_id:
            await self._buffer(piece)
            return
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
        key = (piece.donor, piece.grouped_id)
        self._albums.setdefault(key, []).append(piece)
        if key not in self._tasks:
            self._tasks[key] = asyncio.create_task(self._flush(key))

    async def _flush(self, key: tuple[str, int]) -> None:
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
                signature_template=primary.signature_template,
            ),
            record=True,
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
                "not published @%s %s: %s",
                primary.donor,
                ",".join(str(item) for item in source_ids),
                result.reason,
            )
            return
        await self.publisher.enqueue(
            Outgoing(
                donor=primary.donor,
                source_ids=source_ids,
                text=result.text,
                photos=[blob for blob in photos if blob is not None],
                fingerprint=result.fingerprint,
            )
        )
