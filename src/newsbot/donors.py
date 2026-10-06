"""Owner-managed donor list. No Telegram calls.

The owner adds a public channel by ``@username`` or a ``t.me`` link, turns it
on or off, and deletes it after a confirmation callback. Callback data stays
inside Telegram's 64-byte limit. A per-donor ``signature`` already stored in
config is kept; this module does not invent new settings.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from newsbot.config import Config, ConfigError, Donor, load_config

CALLBACK_LIMIT = 64
USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")
_LINK_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/(?:s/)?"
    r"([A-Za-z][A-Za-z0-9_]{3,31})(?:/\d+)?$",
    re.IGNORECASE,
)
_ACTIONS = {
    "add": "a",
    "back": "b",
    "edit": "e",
    "ask_delete": "k",
    "confirm_delete": "y",
    "enable": "+",
    "disable": "-",
}
_BY_CODE = {code: name for name, code in _ACTIONS.items()}
_CALLBACK_RE = re.compile(r"^dn:([abeky+\-])(?::([A-Za-z][A-Za-z0-9_]{3,31}))?$")
_NEEDS_USERNAME = frozenset({"edit", "ask_delete", "confirm_delete", "enable", "disable"})


class DonorRefError(ValueError):
    """The owner sent something that is not a public channel username."""


@dataclass(frozen=True)
class DonorPrompt:
    kind: str
    username: str | None = None


def parse_donor_ref(raw: str) -> str:
    """Return a public username from ``@name`` or a t.me link.

    Invite links, private ``t.me/c/...`` links, and ``joinchat`` links are
    rejected. The caller still has to check that the username is a channel,
    not a user or a group.
    """
    text = (raw or "").strip()
    if not text:
        raise DonorRefError("Пришлите @username или ссылку t.me/канал.")
    lowered = text.casefold()
    if (
        "joinchat/" in lowered
        or "/+" in text
        or text.startswith("+")
        or "/c/" in lowered
        or lowered.startswith("tg://")
    ):
        raise DonorRefError("Это не публичный канал. Нужен @username или ссылка t.me/канал.")
    if text.startswith("@"):
        name = text[1:]
    else:
        cleaned = text.split("?", 1)[0].split("#", 1)[0].strip().rstrip("/")
        match = _LINK_RE.fullmatch(cleaned)
        if match:
            name = match.group(1)
        elif USERNAME_RE.fullmatch(text):
            name = text
        else:
            raise DonorRefError("Не понял. Пришлите @username или ссылку t.me/канал.")
    if not USERNAME_RE.fullmatch(name):
        raise DonorRefError("Не понял. Пришлите @username или ссылку t.me/канал.")
    return name


def reject_donor_chat(chat_type: str) -> str | None:
    """Return a Russian error unless ``chat_type`` is a public channel."""
    if chat_type == "channel":
        return None
    if chat_type == "private":
        return "Личные чаты не подходят. Нужен публичный канал."
    if chat_type in {"group", "supergroup"}:
        return "Группы не подходят. Нужен публичный канал."
    return "Нужен публичный канал."


def format_donor_list(donors: tuple[Donor, ...]) -> str:
    if not donors:
        return "Список доноров пуст."
    lines = []
    for donor in donors:
        state = "включён" if donor.enabled else "выключен"
        lines.append(f"@{donor.username} — {state}")
    return "\n".join(lines)


def format_donor_edit(donor: Donor) -> str:
    state = "включён" if donor.enabled else "выключен"
    return (
        f"@{donor.username} — {state}\n"
        "Пришлите новый @username или ссылку t.me, чтобы сменить канал."
    )


def format_delete_confirm(username: str) -> str:
    return f"Удалить @{username}?"


def pack_donor_callback(action: str, username: str | None = None) -> str:
    if action not in _ACTIONS:
        raise ValueError(action)
    if action in _NEEDS_USERNAME:
        if username is None or not USERNAME_RE.fullmatch(username):
            raise ValueError("username required")
        data = f"dn:{_ACTIONS[action]}:{username}"
    else:
        if username is not None:
            raise ValueError("username not allowed")
        data = f"dn:{_ACTIONS[action]}"
    if len(data.encode("utf-8")) > CALLBACK_LIMIT:
        raise ValueError("callback data exceeds 64 bytes")
    return data


def parse_donor_callback(data: str | None) -> tuple[str, str | None] | None:
    match = _CALLBACK_RE.fullmatch(data or "")
    if not match:
        return None
    action = _BY_CODE[match.group(1)]
    username = match.group(2)
    if action in _NEEDS_USERNAME and username is None:
        return None
    if action not in _NEEDS_USERNAME and username is not None:
        return None
    return action, username


def donors_keyboard(donors: tuple[Donor, ...]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="Добавить", callback_data=pack_donor_callback("add"))]
    ]
    for donor in donors:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Удалить",
                    callback_data=pack_donor_callback("ask_delete", donor.username),
                ),
                InlineKeyboardButton(
                    text="Редактировать",
                    callback_data=pack_donor_callback("edit", donor.username),
                ),
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def edit_keyboard(donor: Donor) -> InlineKeyboardMarkup:
    if donor.enabled:
        toggle = InlineKeyboardButton(
            text="Выключить",
            callback_data=pack_donor_callback("disable", donor.username),
        )
    else:
        toggle = InlineKeyboardButton(
            text="Включить",
            callback_data=pack_donor_callback("enable", donor.username),
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [toggle],
            [InlineKeyboardButton(text="К списку", callback_data=pack_donor_callback("back"))],
        ]
    )


def confirm_delete_keyboard(username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Удалить",
                    callback_data=pack_donor_callback("confirm_delete", username),
                )
            ],
            [InlineKeyboardButton(text="Отмена", callback_data=pack_donor_callback("back"))],
        ]
    )


def button_labels(markup: InlineKeyboardMarkup) -> str:
    return ",".join(button.text for row in markup.inline_keyboard for button in row)


def find_donor(donors: tuple[Donor, ...], username: str) -> Donor | None:
    key = username.casefold()
    for donor in donors:
        if donor.username.casefold() == key:
            return donor
    return None


def add_donor(donors: tuple[Donor, ...], username: str) -> tuple[tuple[Donor, ...], str | None]:
    if find_donor(donors, username) is not None:
        return donors, "Такой донор уже есть."
    return donors + (Donor(username=username, enabled=True, signature=None),), None


def delete_donor(donors: tuple[Donor, ...], username: str) -> tuple[tuple[Donor, ...], str | None]:
    kept = tuple(donor for donor in donors if donor.username.casefold() != username.casefold())
    if len(kept) == len(donors):
        return donors, "Этого донора уже нет."
    return kept, None


def rename_donor(
    donors: tuple[Donor, ...],
    old: str,
    new: str,
) -> tuple[tuple[Donor, ...], str | None]:
    if find_donor(donors, old) is None:
        return donors, "Этого донора уже нет."
    taken = find_donor(donors, new)
    if taken is not None and taken.username.casefold() != old.casefold():
        return donors, "Такой донор уже есть."
    updated: list[Donor] = []
    for donor in donors:
        if donor.username.casefold() == old.casefold():
            updated.append(Donor(username=new, enabled=donor.enabled, signature=donor.signature))
        else:
            updated.append(donor)
    return tuple(updated), None


def set_donor_enabled(
    donors: tuple[Donor, ...],
    username: str,
    enabled: bool,
) -> tuple[tuple[Donor, ...], str | None]:
    if find_donor(donors, username) is None:
        return donors, "Этого донора уже нет."
    updated: list[Donor] = []
    for donor in donors:
        if donor.username.casefold() == username.casefold():
            updated.append(Donor(username=donor.username, enabled=enabled, signature=donor.signature))
        else:
            updated.append(donor)
    return tuple(updated), None


def apply_donor_action(
    donors: tuple[Donor, ...],
    action: str,
    username: str | None,
    *,
    new_username: str | None = None,
) -> tuple[tuple[Donor, ...], str | None]:
    """Apply a mutating action. Asking to delete does not change the list."""
    if action in {"add", "back", "edit", "ask_delete"}:
        return donors, None
    if username is None:
        return donors, "Этого донора уже нет."
    if action == "confirm_delete":
        return delete_donor(donors, username)
    if action == "enable":
        return set_donor_enabled(donors, username, True)
    if action == "disable":
        return set_donor_enabled(donors, username, False)
    if action == "rename":
        if new_username is None:
            return donors, "Не понял. Пришлите @username или ссылку t.me/канал."
        return rename_donor(donors, username, new_username)
    return donors, "Не понял действие."


def donor_mapping(donor: Donor) -> dict[str, object]:
    item: dict[str, object] = {"username": donor.username, "enabled": donor.enabled}
    if donor.signature:
        item["signature"] = donor.signature
    return item


def save_donor_list(path: str | Path, donors: tuple[Donor, ...]) -> Config:
    """Replace only the ``donors`` key and return the config reloaded from disk."""
    target = Path(path)
    original = target.read_text(encoding="utf-8")
    mode = target.stat().st_mode
    data = yaml.safe_load(original) or {}
    if not isinstance(data, dict):
        raise ConfigError("Корень config.yaml должен быть словарём")
    data["donors"] = [donor_mapping(donor) for donor in donors]
    rendered = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    temporary = target.with_name(target.name + ".tmp")
    try:
        temporary.write_text(rendered, encoding="utf-8")
        os.chmod(temporary, mode)
        os.replace(temporary, target)
        return load_config(target)
    except (Exception, ConfigError):
        if temporary.exists():
            temporary.unlink()
        target.write_text(original, encoding="utf-8")
        os.chmod(target, mode)
        raise


def install_config(runtime: Any, config: Config) -> None:
    """Point the running objects at the reloaded config."""
    runtime.config = config
    pipeline = getattr(runtime, "pipeline", None)
    if pipeline is not None:
        pipeline.config = config
    publisher = getattr(runtime, "publisher", None)
    if publisher is not None:
        publisher.config = config
    review = getattr(runtime, "review", None)
    if review is not None:
        review.config = config
    collector = getattr(runtime, "collector", None)
    if collector is not None:
        collector.config = config
