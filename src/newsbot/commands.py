from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import BotCommand, CallbackQuery, KeyboardButton, Message, ReplyKeyboardMarkup
from telethon.tl.types import MessageService

from newsbot.config import ConfigError
from newsbot.donors import (
    DonorPrompt,
    DonorRefError,
    add_donor,
    apply_donor_action,
    button_labels,
    confirm_delete_keyboard,
    donors_keyboard,
    edit_keyboard,
    find_donor,
    format_delete_confirm,
    format_donor_edit,
    format_donor_list,
    install_config,
    parse_donor_callback,
    parse_donor_ref,
    reject_donor_chat,
    rename_donor,
    save_donor_list,
)
from newsbot.pipeline import PostInput
from newsbot.runtime import Runtime

logger = logging.getLogger(__name__)

START_TEXT = (
    "Бот на связи. "
    "В канале проверки: «Отправить» публикует пост в канал новостей, "
    "«Редактировать» меняет текст, «Отклонить» убирает его."
)

OWNER_BUTTONS = ("Статус", "Доноры", "Пауза", "Продолжить", "Помощь")

BUTTON_ACTIONS = {
    "Статус": "status",
    "Доноры": "donors",
    "Пауза": "pause",
    "Продолжить": "resume",
    "Помощь": "help",
}


def bot_commands() -> list[BotCommand]:
    return [
        BotCommand(command="start", description="Бот на связи"),
        BotCommand(command="status", description="Состояние и ошибки"),
        BotCommand(command="donors", description="Список доноров"),
        BotCommand(command="pause", description="Не брать новые посты"),
        BotCommand(command="resume", description="Снова брать посты"),
        BotCommand(command="help", description="Что делают кнопки"),
        BotCommand(command="preview", description="Предпросмотр без публикации"),
    ]


def owner_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Статус"), KeyboardButton(text="Доноры")],
            [KeyboardButton(text="Пауза"), KeyboardButton(text="Продолжить")],
            [KeyboardButton(text="Помощь")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_router(runtime: Runtime, bot: Bot) -> Router:
    router = Router()
    owner_id = runtime.config.owner_id

    def is_owner(message: Message) -> bool:
        user = message.from_user
        return bool(
            user is not None and user.id == owner_id and message.chat.type == ChatType.PRIVATE
        )

    def owner_markup(message: Message) -> ReplyKeyboardMarkup | None:
        if is_owner(message):
            return owner_keyboard()
        return None

    async def only_owner(message: Message) -> bool:
        if is_owner(message):
            return True
        await message.answer("нет доступа")
        return False

    def clear_donor_prompt() -> None:
        runtime.donor_prompt = None

    async def send_start(message: Message) -> None:
        clear_donor_prompt()
        sent = await message.answer(START_TEXT, reply_markup=owner_markup(message))
        logger.info("outgoing start reply message_id=%s", sent.message_id)

    async def send_donors(message: Message) -> None:
        clear_donor_prompt()
        markup = donors_keyboard(runtime.config.donors)
        sent = await message.answer(format_donor_list(runtime.config.donors), reply_markup=markup)
        logger.info(
            "outgoing donors reply message_id=%s buttons=%s",
            sent.message_id,
            button_labels(markup),
        )

    async def show_donors_editor(message: Message) -> None:
        markup = donors_keyboard(runtime.config.donors)
        try:
            await message.edit_text(format_donor_list(runtime.config.donors), reply_markup=markup)
        except TelegramBadRequest as exc:
            if "not modified" not in str(exc).lower():
                raise
        logger.info(
            "outgoing donors edit message_id=%s buttons=%s",
            message.message_id,
            button_labels(markup),
        )

    def store_donors(donors: tuple) -> str | None:
        if not runtime.config_path:
            return "Не удалось записать конфиг."
        try:
            loaded = save_donor_list(runtime.config_path, donors)
        except (Exception, ConfigError) as exc:
            logger.error("donor save failed: %s", exc.__class__.__name__)
            return "Не удалось записать конфиг."
        install_config(runtime, loaded)
        return None

    @router.message(Command("start"))
    async def start_cmd(message: Message) -> None:
        await send_start(message)

    @router.message(Command("help"))
    async def help_cmd(message: Message) -> None:
        await send_start(message)

    @router.message(F.text.in_(OWNER_BUTTONS))
    async def button_cmd(message: Message) -> None:
        action = BUTTON_ACTIONS.get(message.text or "")
        if action == "help":
            await send_start(message)
            return
        if not await only_owner(message):
            return
        markup = owner_keyboard()
        if action == "status":
            clear_donor_prompt()
            await message.answer(_status_text(runtime), reply_markup=markup)
        elif action == "donors":
            await send_donors(message)
        elif action == "pause":
            clear_donor_prompt()
            runtime.db.set_paused(True)
            logger.info("publishing paused by owner")
            await message.answer(
                "Пауза: новые посты не попадают в канал проверки. "
                "Уже выложенные там кнопки по-прежнему работают.",
                reply_markup=markup,
            )
        elif action == "resume":
            clear_donor_prompt()
            runtime.db.set_paused(False)
            logger.info("publishing resumed by owner")
            await message.answer("Публикация продолжена.", reply_markup=markup)

    @router.message(Command("status"))
    async def status_cmd(message: Message) -> None:
        if not await only_owner(message):
            return
        clear_donor_prompt()
        await message.answer(_status_text(runtime), reply_markup=owner_keyboard())

    @router.message(Command("pause"))
    async def pause_cmd(message: Message) -> None:
        if not await only_owner(message):
            return
        clear_donor_prompt()
        runtime.db.set_paused(True)
        logger.info("publishing paused by owner")
        await message.answer(
            "Пауза: новые посты не попадают в канал проверки. "
            "Уже выложенные там кнопки по-прежнему работают.",
            reply_markup=owner_keyboard(),
        )

    @router.message(Command("resume"))
    async def resume_cmd(message: Message) -> None:
        if not await only_owner(message):
            return
        clear_donor_prompt()
        runtime.db.set_paused(False)
        logger.info("publishing resumed by owner")
        await message.answer("Публикация продолжена.", reply_markup=owner_keyboard())

    @router.message(Command("donors"))
    async def donors_cmd(message: Message) -> None:
        if not await only_owner(message):
            return
        await send_donors(message)

    @router.message(Command("preview"))
    async def preview_cmd(message: Message) -> None:
        if not await only_owner(message):
            return
        clear_donor_prompt()
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await message.answer("Использование: /preview <username донора>")
            return
        await message.answer(await _preview(runtime, parts[1].strip()), reply_markup=owner_keyboard())

    @router.callback_query(F.data.startswith("dn:"))
    async def donor_callback(query: CallbackQuery) -> None:
        user = query.from_user
        if user is None or user.id != owner_id:
            await query.answer("нет доступа")
            return
        parsed = parse_donor_callback(query.data)
        if parsed is None or query.message is None:
            await query.answer()
            return
        action, username = parsed
        await query.answer()
        if action == "add":
            runtime.donor_prompt = DonorPrompt("add")
            await query.message.answer(
                "Пришлите публичный канал: @username или ссылку t.me/канал. Отмена — /donors."
            )
            return
        if action == "back":
            clear_donor_prompt()
            await show_donors_editor(query.message)
            return
        if action == "ask_delete":
            clear_donor_prompt()
            if username is None or find_donor(runtime.config.donors, username) is None:
                await show_donors_editor(query.message)
                return
            markup = confirm_delete_keyboard(username)
            await query.message.edit_text(format_delete_confirm(username), reply_markup=markup)
            logger.info(
                "outgoing donors edit message_id=%s buttons=%s",
                query.message.message_id,
                button_labels(markup),
            )
            return
        if action == "edit":
            donor = find_donor(runtime.config.donors, username or "")
            if donor is None:
                clear_donor_prompt()
                await show_donors_editor(query.message)
                return
            runtime.donor_prompt = DonorPrompt("rename", donor.username)
            markup = edit_keyboard(donor)
            await query.message.edit_text(format_donor_edit(donor), reply_markup=markup)
            logger.info(
                "outgoing donors edit message_id=%s buttons=%s",
                query.message.message_id,
                button_labels(markup),
            )
            return
        updated, error = apply_donor_action(runtime.config.donors, action, username)
        if error:
            await query.message.answer(error)
            await show_donors_editor(query.message)
            return
        stored = store_donors(updated)
        if stored:
            await query.message.answer(stored)
            return
        if action in {"enable", "disable"}:
            donor = find_donor(runtime.config.donors, username or "")
            if donor is None:
                clear_donor_prompt()
                await show_donors_editor(query.message)
                return
            runtime.donor_prompt = DonorPrompt("rename", donor.username)
            markup = edit_keyboard(donor)
            await query.message.edit_text(format_donor_edit(donor), reply_markup=markup)
            logger.info(
                "outgoing donors edit message_id=%s buttons=%s",
                query.message.message_id,
                button_labels(markup),
            )
            return
        clear_donor_prompt()
        await show_donors_editor(query.message)

    @router.message(F.chat.type == ChatType.PRIVATE, F.text, _donor_prompt_open(runtime))
    async def donor_text(message: Message) -> None:
        prompt = runtime.donor_prompt
        if prompt is None or not is_owner(message):
            return
        try:
            username = parse_donor_ref(message.text or "")
        except DonorRefError as exc:
            await message.answer(str(exc))
            return
        rejected = await _public_channel_error(bot, username)
        if rejected:
            await message.answer(rejected)
            return
        if prompt.kind == "rename":
            updated, error = rename_donor(runtime.config.donors, prompt.username or "", username)
        else:
            updated, error = add_donor(runtime.config.donors, username)
        if error:
            await message.answer(error)
            return
        stored = store_donors(updated)
        if stored:
            await message.answer(stored)
            return
        clear_donor_prompt()
        await send_donors(message)

    return router


def _donor_prompt_open(runtime: Runtime):
    def check(message: Message) -> bool:
        prompt = runtime.donor_prompt
        if prompt is None or message.from_user is None:
            return False
        if message.from_user.id != runtime.config.owner_id:
            return False
        if message.chat.type != ChatType.PRIVATE:
            return False
        text = message.text or ""
        if text.startswith("/") or text in OWNER_BUTTONS:
            return False
        return True

    return check


async def _public_channel_error(bot: Bot, username: str) -> str | None:
    try:
        chat = await bot.get_chat(f"@{username}")
    except TelegramBadRequest:
        return "Не нашёл публичный канал с таким именем."
    except Exception as exc:
        logger.error("donor lookup failed: %s", exc.__class__.__name__)
        return "Не удалось проверить канал."
    chat_type = getattr(chat.type, "value", None)
    if not isinstance(chat_type, str) or not chat_type:
        chat_type = str(chat.type)
    if chat_type.startswith("ChatType."):
        chat_type = chat_type.split(".", 1)[1].casefold()
    return reject_donor_chat(chat_type)


def _status_text(runtime: Runtime) -> str:
    donors = runtime.config.donors
    enabled = sum(1 for donor in donors if donor.enabled)
    lines = [
        f"Состояние: {'пауза' if runtime.db.is_paused() else 'работает'}",
        f"Цель: {runtime.config.target_channel}",
        f"Доноры: {len(donors)} (включено {enabled})",
        f"На проверке: {runtime.db.count_pending_previews()}",
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
    if runtime.client is None:
        return "Сессия пользователя не авторизована. Чтение доноров выключено."
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
