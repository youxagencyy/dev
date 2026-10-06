"""Review-queue decisions. No Telegram calls.

Callback data is ``s:<id>``, ``e:<id>`` or ``r:<id>`` so it stays inside
Telegram's 64-byte limit. Only ``owner_id`` moves a pending preview.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_CALLBACK = re.compile(r"^([ser]):([1-9]\d{0,17})$")
_PREFIX = {"send": "s", "edit": "e", "reject": "r"}
_ACTION = {"s": "send", "e": "edit", "r": "reject"}
CALLBACK_LIMIT = 64


@dataclass(frozen=True)
class Route:
    effect: str
    state: str


@dataclass(frozen=True)
class EditChoice:
    preview_id: int | None = None
    ambiguous: bool = False


def pack_callback(action: str, preview_id: int) -> str:
    if action not in _PREFIX:
        raise ValueError(action)
    if preview_id < 1:
        raise ValueError("preview id must be positive")
    data = f"{_PREFIX[action]}:{preview_id}"
    if len(data.encode("utf-8")) > CALLBACK_LIMIT:
        raise ValueError("callback data exceeds 64 bytes")
    return data


def parse_callback(data: str | None) -> tuple[str, int] | None:
    match = _CALLBACK.fullmatch(data or "")
    if not match:
        return None
    return _ACTION[match.group(1)], int(match.group(2))


def route_callback(action: str, *, actor_id: int | None, owner_id: int, state: str) -> Route:
    """Decide what a button press does. The returned state is the next state.

    ``edit`` stays ``pending``. Presses from anyone except the owner, and
    presses on a preview that is already sent or rejected, do not change it.
    """
    if actor_id != owner_id or action not in _PREFIX:
        return Route("ignore", state)
    if state != "pending":
        return Route("stale", state)
    if action == "send":
        return Route("send", "sent")
    if action == "reject":
        return Route("reject", "rejected")
    return Route("edit", "pending")


def preview_heading(branch_name: str) -> str:
    name = (branch_name or "").strip() or "Новости"
    return f"Ветка: {name}"


def preview_label(branch_name: str, text: str) -> str:
    """Log-channel text. The stored body stays unlabeled so publish does not repeat the name."""
    heading = preview_heading(branch_name)
    body = (text or "").strip()
    if not body:
        return heading
    return f"{heading}\n\n{body}"


def preview_publish_channel(stored: str, fallback: str) -> str:
    text = (stored or "").strip()
    return text or fallback


def sent_status(message_ids: list[int]) -> str:
    shown = ", ".join(str(item) for item in message_ids) or "—"
    return f"Отправлено → {shown}"


def rejected_status() -> str:
    return "Отклонено"


def choose_private_edit(
    prompts: list[tuple[int, int | None]],
    reply_to_id: int | None,
) -> EditChoice:
    """Pick which pending preview a private message should rewrite.

    ``prompts`` is ``(preview_id, edit_prompt_message_id)`` for previews that
    are waiting for a new text. A reply to one prompt wins. A plain message
    is used only when exactly one prompt is open.
    """
    if reply_to_id is not None:
        for preview_id, prompt_id in prompts:
            if prompt_id == reply_to_id:
                return EditChoice(preview_id=preview_id)
        return EditChoice()
    waiting = [preview_id for preview_id, prompt_id in prompts if prompt_id is not None]
    if len(waiting) == 1:
        return EditChoice(preview_id=waiting[0])
    if len(waiting) > 1:
        return EditChoice(ambiguous=True)
    return EditChoice()


def match_log_reply(
    rows: list[tuple[int, int | None, int | None]],
    replied_message_id: int,
) -> int | None:
    """Match a reply in the log channel to a pending preview message."""
    for preview_id, log_message_id, content_message_id in rows:
        if replied_message_id in {log_message_id, content_message_id}:
            return preview_id
    return None
