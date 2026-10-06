"""Post cleaned items into the log channel and apply the owner's decision."""

from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)

from newsbot.config import Config, chat_target
from newsbot.db import Database
from newsbot.dedupe import Deduper
from newsbot.commands import OWNER_BUTTONS
from newsbot.publisher import Outgoing, Publisher
from newsbot.branches import materialize_branches
from newsbot.review import (
    choose_private_edit,
    match_log_reply,
    pack_callback,
    parse_callback,
    preview_heading,
    preview_label,
    preview_publish_channel,
    rejected_status,
    route_callback,
    sent_status,
)
from newsbot.textutil import fit_text

logger = logging.getLogger(__name__)

EDIT_PROMPT = (
    "Ответьте на это сообщение новым текстом. "
    "Кнопки «Отправить», «Редактировать» и «Отклонить» остаются. "
    "В канал публикации оно не уйдёт, пока не нажмёте «Отправить»."
)


def review_keyboard(preview_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Отправить", callback_data=pack_callback("send", preview_id)),
                InlineKeyboardButton(
                    text="Редактировать",
                    callback_data=pack_callback("edit", preview_id),
                ),
                InlineKeyboardButton(text="Отклонить", callback_data=pack_callback("reject", preview_id)),
            ]
        ]
    )


def _cleared_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[])


class ReviewQueue:
    def __init__(self, bot, config: Config, db: Database, publisher: Publisher, deduper: Deduper) -> None:
        self.bot = bot
        self.config = config
        self.db = db
        self.publisher = publisher
        self.deduper = deduper
        self._lock = asyncio.Lock()

    async def submit(
        self,
        *,
        donor: str,
        source_ids: list[int],
        text: str,
        photos: list[bytes],
        dedupe_text: str,
        branch_name: str = "",
        publish_channel: str = "",
        review_channel: str = "",
    ) -> int | None:
        """Put one cleaned post in that branch's review channel. Nothing is published yet."""
        branch = branch_name or self.config.current_branch or "Новости"
        target = publish_channel or self.config.target_channel
        review = review_channel or self.config.log_channel
        shown = preview_label(branch, text)
        preview_id = self.db.create_preview(
            donor=donor,
            source_message_ids=source_ids,
            log_chat_id=review,
            text=text,
            dedupe_text=dedupe_text,
            branch_name=branch,
            target_channel=target,
        )
        if photos:
            self.db.save_preview_media(preview_id, photos)
        chat = chat_target(review)
        markup = review_keyboard(preview_id)
        try:
            if not photos:
                sent = await self.bot.send_message(chat, shown, reply_markup=markup)
                self.db.attach_preview_message(
                    preview_id,
                    log_message_id=sent.message_id,
                    content_message_id=sent.message_id,
                    kind="text",
                )
            elif len(photos) == 1:
                sent = await self.bot.send_photo(
                    chat,
                    BufferedInputFile(photos[0], filename="photo.jpg"),
                    caption=shown or None,
                    reply_markup=markup,
                )
                self.db.attach_preview_message(
                    preview_id,
                    log_message_id=sent.message_id,
                    content_message_id=sent.message_id,
                    kind="photo",
                )
            else:
                media = [
                    InputMediaPhoto(
                        media=BufferedInputFile(blob, filename=f"photo-{index}.jpg"),
                        caption=shown if index == 0 and shown else None,
                    )
                    for index, blob in enumerate(photos[: self.config.publish.album_max_items])
                ]
                group = await self.bot.send_media_group(chat, media)
                control = await self.bot.send_message(
                    chat,
                    f"{preview_heading(branch)}\nПроверка альбома",
                    reply_markup=markup,
                )
                self.db.attach_preview_message(
                    preview_id,
                    log_message_id=control.message_id,
                    content_message_id=group[0].message_id,
                    kind="album",
                )
        except Exception as exc:
            logger.exception("review post failed for @%s", donor)
            self.db.add_error("review", exc.__class__.__name__)
            self.db.transition_preview(preview_id, "rejected", expect="pending")
            return None
        logger.info("review queued donor=@%s preview=%s", donor, preview_id)
        return preview_id

    async def on_callback(self, query: CallbackQuery) -> None:
        actor_id = query.from_user.id if query.from_user else None
        parsed = parse_callback(query.data)
        if parsed is None:
            await answer_callback(query)
            return
        action, preview_id = parsed
        if action == "edit":
            if actor_id != self.config.owner_id:
                await answer_callback(query, "нет доступа")
                return
            # Stop the spinner before any database or send work. A stale query
            # still gets the private prompt.
            await deliver_edit_prompt(self.bot, self.config.owner_id, query, self.db, preview_id)
            return
        async with self._lock:
            preview = self.db.get_preview(preview_id)
            if preview is None:
                await answer_callback(query)
                return
            decision = route_callback(
                action,
                actor_id=actor_id,
                owner_id=self.config.owner_id,
                state=preview.state,
            )
            if decision.effect == "ignore":
                await answer_callback(query)
                return
            if decision.effect == "stale":
                await answer_callback(query, "Уже обработано")
                return
            if decision.effect == "reject":
                if not self.db.transition_preview(preview_id, "rejected", expect="pending"):
                    await answer_callback(query, "Уже обработано")
                    return
                fresh = self.db.get_preview(preview_id)
                if fresh is not None:
                    await self._show_status(fresh, rejected_status())
                await answer_callback(query, "Отклонено")
                return
            photos = self.db.preview_media(preview_id)
            source_ids = [int(item) for item in preview.source_message_ids.split(",") if item]
            channel = preview_publish_channel(preview.target_channel, self.config.target_channel)
            try:
                target_ids = await self.publisher.publish_now(
                    Outgoing(
                        donor=preview.donor,
                        source_ids=source_ids,
                        text=preview.text,
                        photos=photos,
                        fingerprint="",
                    ),
                    channel=channel,
                )
            except Exception as exc:
                logger.exception("approved publish failed preview=%s", preview_id)
                self.db.add_error("publish", exc.__class__.__name__)
                await answer_callback(query, "Не удалось отправить")
                return
            if not self.db.transition_preview(
                preview_id,
                "sent",
                expect="pending",
                target_message_ids=target_ids,
            ):
                await answer_callback(query, "Уже обработано")
                return
            if preview.dedupe_text.strip():
                self.deduper.remember(
                    preview.dedupe_text,
                    donor=preview.donor,
                    message_id=source_ids[0] if source_ids else preview_id,
                )
            self.db.log_publish(
                donor=preview.donor,
                source_message_ids=source_ids,
                target_message_ids=target_ids,
                fingerprint="",
                status="published",
            )
            fresh = self.db.get_preview(preview_id)
            if fresh is not None:
                await self._show_status(fresh, sent_status(target_ids))
            await answer_callback(query, "Отправлено")

    async def receive_edit(self, message: Message) -> None:
        user = message.from_user
        if user is None or user.id != self.config.owner_id:
            return
        text = (message.text or "").strip()
        if not text or text.startswith("/") or text in OWNER_BUTTONS:
            return
        reply_id = message.reply_to_message.message_id if message.reply_to_message else None
        if message.chat.type != ChatType.PRIVATE and not self._is_log_chat(message.chat.id):
            return
        if message.chat.type == ChatType.PRIVATE:
            choice = choose_private_edit(self.db.pending_edit_prompts(), reply_id)
            if choice.ambiguous:
                await message.answer("Ответьте на сообщение бота с номером превью.")
                return
            preview_id = choice.preview_id
        else:
            if reply_id is None:
                return
            preview_id = match_log_reply(self.db.pending_review_messages(), reply_id)
        if preview_id is None:
            return
        await self._apply_new_text(preview_id, text, message)

    async def _apply_new_text(self, preview_id: int, text: str, message: Message) -> None:
        async with self._lock:
            preview = self.db.get_preview(preview_id)
            if preview is None or preview.state != "pending":
                await message.answer("Это превью уже закрыто.")
                return
            limit = (
                self.config.publish.message_limit
                if preview.kind == "text"
                else self.config.publish.caption_limit
            )
            fitted = fit_text(text, limit)
            if not self.db.replace_preview_text(preview_id, fitted):
                await message.answer("Это превью уже закрыто.")
                return
            preview = self.db.get_preview(preview_id)
            if preview is None:
                return
            try:
                await self._replace_body(preview, fitted, keep_buttons=True)
            except Exception as exc:
                logger.exception("preview text edit failed")
                self.db.add_error("review", exc.__class__.__name__)
                await message.answer("Текст сохранён, но сообщение в канале проверки не обновилось.")
                return
            self.db.clear_edit_prompt(preview_id)
            await message.answer("Текст обновлён. Кнопки на месте, в канал публикации ещё не отправлено.")

    async def _replace_body(self, preview, text: str, *, keep_buttons: bool) -> None:
        chat = chat_target(preview.log_chat_id)
        shown = preview_label(preview.branch_name, text)
        markup = review_keyboard(preview.id) if keep_buttons else _cleared_keyboard()
        if preview.kind == "text" and preview.log_message_id is not None:
            await self._edit_text(chat, preview.log_message_id, shown, markup)
            return
        if preview.kind == "photo" and preview.log_message_id is not None:
            await self._edit_caption(chat, preview.log_message_id, shown, markup)
            return
        if preview.content_message_id is not None:
            await self._edit_caption(chat, preview.content_message_id, shown, None)

    async def _show_status(self, preview, status: str) -> None:
        chat = chat_target(preview.log_chat_id)
        cleared = _cleared_keyboard()
        try:
            if preview.kind == "album" and preview.log_message_id is not None:
                await self._edit_text(chat, preview.log_message_id, status, cleared)
                return
            limit = (
                self.config.publish.message_limit
                if preview.kind == "text"
                else self.config.publish.caption_limit
            )
            body = fit_text(f"{preview_label(preview.branch_name, preview.text).rstrip()}\n\n{status}", limit)
            if preview.kind == "photo" and preview.log_message_id is not None:
                await self._edit_caption(chat, preview.log_message_id, body, cleared)
            elif preview.log_message_id is not None:
                await self._edit_text(chat, preview.log_message_id, body, cleared)
        except Exception as exc:
            logger.exception("review status edit failed")
            self.db.add_error("review", exc.__class__.__name__)

    async def _edit_text(self, chat, message_id: int, text: str, markup) -> None:
        kwargs = {"chat_id": chat, "message_id": message_id, "reply_markup": markup}
        try:
            await self.bot.edit_message_text(text, **kwargs)
        except TelegramBadRequest as exc:
            if "not modified" not in str(exc).lower():
                raise

    async def _edit_caption(self, chat, message_id: int, caption: str, markup) -> None:
        kwargs = {"chat_id": chat, "message_id": message_id, "caption": caption or None}
        if markup is not None:
            kwargs["reply_markup"] = markup
        try:
            await self.bot.edit_message_caption(**kwargs)
        except TelegramBadRequest as exc:
            if "not modified" not in str(exc).lower():
                raise

    def _is_log_chat(self, chat_id: int) -> bool:
        for branch in materialize_branches(self.config):
            if chat_id == chat_target(branch.review_channel):
                return True
        return False


async def answer_callback(query: CallbackQuery, text: str | None = None) -> None:
    try:
        if text:
            await query.answer(text)
        else:
            await query.answer()
    except TelegramBadRequest:
        logger.info("callback answer skipped")


async def deliver_edit_prompt(bot, owner_id: int, query: CallbackQuery, db, preview_id: int) -> int:
    """Answer Редактировать, then ask the owner for a new text. Does not publish."""
    await answer_callback(query)
    preview = db.get_preview(preview_id)
    if preview is None or preview.state != "pending":
        sent = await bot.send_message(owner_id, "Это превью уже закрыто.")
        logger.info("outgoing edit closed message_id=%s preview=%s", sent.message_id, preview_id)
        return sent.message_id
    sent = await bot.send_message(owner_id, f"Превью {preview_id}. {EDIT_PROMPT}")
    db.set_edit_prompt(preview_id, sent.message_id)
    logger.info("outgoing edit prompt message_id=%s preview=%s", sent.message_id, preview_id)
    return sent.message_id


def build_review_router(queue: ReviewQueue) -> Router:
    router = Router()
    owner_id = queue.config.owner_id

    @router.callback_query(
        ~F.data.startswith("dn:") & ~F.data.startswith("br:") & ~F.data.startswith("tm:")
    )
    async def on_callback(query: CallbackQuery) -> None:
        await queue.on_callback(query)

    @router.message(F.chat.type == ChatType.PRIVATE, F.text)
    async def on_private_text(message: Message) -> None:
        if message.from_user is None or message.from_user.id != owner_id:
            return
        if (message.text or "").startswith("/"):
            return
        await queue.receive_edit(message)

    @router.message(F.reply_to_message, F.text)
    async def on_log_reply(message: Message) -> None:
        if message.chat.type == ChatType.PRIVATE:
            return
        if message.from_user is None or message.from_user.id != owner_id:
            return
        await queue.receive_edit(message)

    @router.channel_post(F.reply_to_message, F.text)
    async def on_channel_reply(message: Message) -> None:
        # A broadcast channel post usually has no from_user. Only an identifiable
        # owner may rewrite the preview; otherwise the private prompt is the path.
        if message.from_user is None or message.from_user.id != owner_id:
            return
        await queue.receive_edit(message)

    return router
