from __future__ import annotations

import logging
from typing import Any

from aiogram import Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message
from telethon.tl.types import MessageService

from newsbot.pipeline import PostInput
from newsbot.runtime import Runtime

logger = logging.getLogger(__name__)


def build_router(runtime: Runtime) -> Router:
    router = Router()
    owner_id = runtime.config.owner_id

    def is_owner(message: Message) -> bool:
        user = message.from_user
        return bool(
            user is not None and user.id == owner_id and message.chat.type == ChatType.PRIVATE
        )

    @router.message(Command("status"))
    async def status_cmd(message: Message) -> None:
        if not is_owner(message):
            return
        await message.answer(_status_text(runtime))

    @router.message(Command("pause"))
    async def pause_cmd(message: Message) -> None:
        if not is_owner(message):
            return
        runtime.db.set_paused(True)
        logger.info("publishing paused by owner")
        await message.answer(
            "Публикация на паузе. Новые посты доноров пропускаются и не копятся в очереди."
        )

    @router.message(Command("resume"))
    async def resume_cmd(message: Message) -> None:
        if not is_owner(message):
            return
        runtime.db.set_paused(False)
        logger.info("publishing resumed by owner")
        await message.answer("Публикация продолжена.")

    @router.message(Command("donors"))
    async def donors_cmd(message: Message) -> None:
        if not is_owner(message):
            return
        lines = []
        for donor in runtime.config.donors:
            state = "включён" if donor.enabled else "выключен"
            signature = donor.signature or runtime.config.signatures.default
            lines.append(f"@{donor.username} — {state}, подпись: {signature}")
        await message.answer("Доноры:\n" + "\n".join(lines))

    @router.message(Command("preview"))
    async def preview_cmd(message: Message) -> None:
        if not is_owner(message):
            return
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await message.answer("Использование: /preview <username донора>")
            return
        await message.answer(await _preview(runtime, parts[1].strip()))

    return router


def _status_text(runtime: Runtime) -> str:
    donors = runtime.config.donors
    enabled = sum(1 for donor in donors if donor.enabled)
    lines = [
        f"Состояние: {'пауза' if runtime.db.is_paused() else 'работает'}",
        f"Цель: {runtime.config.target_channel}",
        f"Доноры: {len(donors)} (включено {enabled})",
        f"Очередь публикации: {runtime.publisher.qsize()}",
        "Последние ошибки:",
    ]
    errors = runtime.db.recent_errors(5)
    if not errors:
        lines.append("— нет")
    else:
        for error in errors:
            lines.append(f"— {error.created_at} [{error.context}] {error.message}")
    lines.append("Последние записи журнала:")
    publishes = runtime.db.recent_publishes(5)
    if not publishes:
        lines.append("— нет")
    else:
        for row in publishes:
            target = row.target_message_ids or "—"
            lines.append(
                f"— {row.created_at} @{row.donor} src={row.source_message_ids} "
                f"dst={target} {row.status} {row.reason}".rstrip()
            )
    text = "\n".join(lines)
    return text[:4000]


async def _preview(runtime: Runtime, raw_username: str) -> str:
    username = raw_username.lstrip("@")
    donor = next(
        (
            item
            for item in runtime.config.donors
            if item.username.casefold() == username.casefold() and item.enabled
        ),
        None,
    )
    if donor is None:
        return "Такого включённого донора нет. Список: /donors"
    client: Any = runtime.client
    try:
        entity = await client.get_entity(donor.username)
    except Exception as exc:
        runtime.db.add_error("preview", f"@{donor.username}: {exc.__class__.__name__}")
        return f"Не удалось открыть @{donor.username}."
    if not getattr(entity, "broadcast", False):
        return f"@{donor.username} не канал. Бот читает только каналы из конфига."
    try:
        fetched = await client.get_messages(entity, limit=20)
    except Exception as exc:
        runtime.db.add_error("preview", f"@{donor.username}: {exc.__class__.__name__}")
        return f"Не удалось прочитать @{donor.username}."
    messages = [item for item in fetched if item is not None]
    if not messages:
        return f"В @{donor.username} нет сообщений."
    latest = messages[0]
    grouped_id = getattr(latest, "grouped_id", None)
    if grouped_id:
        group = [item for item in messages if getattr(item, "grouped_id", None) == grouped_id]
    else:
        group = [latest]
    group = sorted(group, key=lambda item: item.id)
    text = max((item.message or "" for item in group), key=len)
    has_photo = any(getattr(item, "photo", None) for item in group)
    is_service = all(
        isinstance(item, MessageService) or getattr(item, "action", None) for item in group
    )
    result = await runtime.pipeline.run(
        PostInput(
            donor=donor.username,
            message_id=latest.id,
            text=text,
            is_service=is_service,
            has_photo=has_photo,
            signature_template=donor.signature,
        ),
        record=False,
    )
    photo_count = sum(1 for item in group if getattr(item, "photo", None))
    header = (
        f"Донор: @{donor.username}\n"
        f"Сообщение: {latest.id}\n"
        f"Решение: {result.action}\n"
        f"Причина: {result.reason or '—'}\n"
        f"Фото: {photo_count}\n\n"
    )
    body = result.text or "—"
    logger.info("preview @%s #%s -> %s", donor.username, latest.id, result.action)
    return (header + body)[:4000]
