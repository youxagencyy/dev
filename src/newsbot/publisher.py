from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.types import BufferedInputFile, InputMediaPhoto

from newsbot.config import Config, chat_target
from newsbot.db import Database
from newsbot.rate_limit import RateLimiter

logger = logging.getLogger(__name__)


@dataclass
class Outgoing:
    donor: str
    source_ids: list[int]
    text: str
    photos: list[bytes] = field(default_factory=list)
    fingerprint: str = ""


class Publisher:
    def __init__(self, bot: Bot, config: Config, db: Database, limiter: RateLimiter) -> None:
        self.bot = bot
        self.config = config
        self.db = db
        self.limiter = limiter
        self.queue: asyncio.Queue[Outgoing | None] = asyncio.Queue()

    def qsize(self) -> int:
        return self.queue.qsize()

    async def enqueue(self, item: Outgoing) -> None:
        await self.queue.put(item)

    async def publish_now(self, item: Outgoing, *, channel: str | None = None) -> list[int]:
        """Publish one approved preview. The review lock is the only caller."""
        await self.limiter.wait()
        return await self._send_with_retry(item, channel=channel)

    async def worker(self) -> None:
        while True:
            item = await self.queue.get()
            if item is None:
                self.queue.task_done()
                return
            try:
                await self._publish(item)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("publish failed for @%s", item.donor)
                self.db.add_error("publish", f"{exc.__class__.__name__}: {item.donor}")
                self.db.log_publish(
                    donor=item.donor,
                    source_message_ids=item.source_ids,
                    target_message_ids=None,
                    fingerprint=item.fingerprint,
                    status="error",
                    reason=exc.__class__.__name__,
                )
            finally:
                self.queue.task_done()

    async def stop(self) -> None:
        await self.queue.put(None)

    async def _publish(self, item: Outgoing) -> None:
        while self.db.is_paused():
            await asyncio.sleep(0.5)
        await self.limiter.wait()
        target_ids = await self._send_with_retry(item, channel=None)
        self.db.log_publish(
            donor=item.donor,
            source_message_ids=item.source_ids,
            target_message_ids=target_ids,
            fingerprint=item.fingerprint,
            status="published",
        )
        logger.info(
            "published donor=@%s source=%s target=%s",
            item.donor,
            ",".join(str(item_id) for item_id in item.source_ids),
            ",".join(str(item_id) for item_id in target_ids),
        )

    async def _send_with_retry(self, item: Outgoing, *, channel: str | None = None) -> list[int]:
        delay = 2.0
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return await self._send(item, channel=channel)
            except TelegramRetryAfter as exc:
                last_error = exc
                await asyncio.sleep(exc.retry_after + 1)
            except TelegramAPIError as exc:
                last_error = exc
                if attempt == 2:
                    raise
                await asyncio.sleep(delay)
                delay *= 2
        if last_error:
            raise last_error
        raise RuntimeError("publish failed")

    async def _send(self, item: Outgoing, *, channel: str | None = None) -> list[int]:
        chat = chat_target(channel or self.config.target_channel)
        photos = item.photos[: self.config.publish.album_max_items]
        caption = item.text or None
        if not photos:
            sent = await self.bot.send_message(chat, item.text)
            return [sent.message_id]
        if len(photos) == 1:
            sent = await self.bot.send_photo(
                chat,
                BufferedInputFile(photos[0], filename="photo.jpg"),
                caption=caption,
            )
            return [sent.message_id]
        media: list[InputMediaPhoto] = []
        for index, blob in enumerate(photos):
            media.append(
                InputMediaPhoto(
                    media=BufferedInputFile(blob, filename=f"photo-{index}.jpg"),
                    caption=caption if index == 0 else None,
                )
            )
        sent_group = await self.bot.send_media_group(chat, media)
        return [message.message_id for message in sent_group]
