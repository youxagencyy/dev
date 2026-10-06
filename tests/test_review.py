import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import AnswerCallbackQuery

from newsbot.config import parse_config
from newsbot.db import Database
from newsbot.review import (
    choose_private_edit,
    match_log_reply,
    pack_callback,
    parse_callback,
    rejected_status,
    route_callback,
    sent_status,
)
from aiogram.enums import ChatType

from newsbot.review_queue import EDIT_HINT, ReviewQueue, deliver_edit_prompt


def test_callback_data_stays_within_64_bytes():
    for action in ("send", "edit", "reject"):
        data = pack_callback(action, 10**15)
        assert len(data.encode("utf-8")) <= 64
        assert parse_callback(data) == (action, 10**15)


def test_callback_rejects_garbage_and_huge_ids():
    assert parse_callback(None) is None
    assert parse_callback("") is None
    assert parse_callback("send:1") is None
    assert parse_callback("s:0") is None
    assert parse_callback("s:01") is None
    with pytest.raises(ValueError):
        pack_callback("send", 10**80)


def test_owner_routes_pending_preview():
    assert route_callback("send", actor_id=7, owner_id=7, state="pending").effect == "send"
    assert route_callback("send", actor_id=7, owner_id=7, state="pending").state == "sent"
    assert route_callback("reject", actor_id=7, owner_id=7, state="pending").state == "rejected"
    edit = route_callback("edit", actor_id=7, owner_id=7, state="pending")
    assert edit.effect == "edit"
    assert edit.state == "pending"


def test_stranger_and_closed_preview_do_not_change_state():
    ignored = route_callback("send", actor_id=2, owner_id=7, state="pending")
    assert ignored.effect == "ignore"
    assert ignored.state == "pending"
    assert route_callback("reject", actor_id=None, owner_id=7, state="pending").effect == "ignore"
    sent = route_callback("send", actor_id=7, owner_id=7, state="sent")
    assert sent.effect == "stale"
    assert sent.state == "sent"
    rejected = route_callback("edit", actor_id=7, owner_id=7, state="rejected")
    assert rejected.effect == "stale"
    assert rejected.state == "rejected"


def test_status_lines():
    assert sent_status([15, 16]) == "Отправлено → 15, 16"
    assert rejected_status() == "Отклонено"


def test_private_edit_choice():
    prompts = [(1, 100), (2, 200)]
    assert choose_private_edit(prompts, 200).preview_id == 2
    assert choose_private_edit(prompts, None).ambiguous is True
    assert choose_private_edit([(4, 10)], None).preview_id == 4
    assert choose_private_edit([], None).preview_id is None
    assert choose_private_edit(prompts, 999).preview_id is None


def test_log_reply_matches_preview_message():
    rows = [(5, 50, 51), (6, 60, 60)]
    assert match_log_reply(rows, 51) == 5
    assert match_log_reply(rows, 60) == 6
    assert match_log_reply(rows, 1) is None


def test_sqlite_transitions_and_text_edit(tmp_path):
    db = Database(tmp_path / "previews.sqlite")
    db.init()
    preview_id = db.create_preview(
        donor="sample",
        source_message_ids=[3],
        log_chat_id="-1001234567890",
        text="Готовый текст",
        dedupe_text="готовый текст",
    )
    db.save_preview_media(preview_id, [b"img"])
    assert db.preview_media(preview_id) == [b"img"]
    assert db.replace_preview_text(preview_id, "Новый текст")
    assert db.get_preview(preview_id).state == "pending"
    assert db.get_preview(preview_id).text == "Новый текст"
    assert db.set_edit_prompt(preview_id, 77)
    assert db.pending_edit_prompts() == [(preview_id, 77)]
    assert db.transition_preview(preview_id, "sent", expect="pending", target_message_ids=[42])
    saved = db.get_preview(preview_id)
    assert saved.state == "sent"
    assert saved.target_message_ids == "42"
    assert db.replace_preview_text(preview_id, "поздно") is False
    assert db.transition_preview(preview_id, "rejected", expect="pending") is False
    assert db.get_preview(preview_id).text == "Новый текст"
    assert db.count_pending_previews() == 0


def test_reject_from_pending(tmp_path):
    db = Database(tmp_path / "previews.sqlite")
    db.init()
    preview_id = db.create_preview(
        donor="sample",
        source_message_ids=[1, 2],
        log_chat_id="-1001234567890",
        text="Текст",
        dedupe_text="",
    )
    assert db.transition_preview(preview_id, "rejected", expect="pending")
    assert db.get_preview(preview_id).state == "rejected"
    assert db.count_pending_previews() == 0


def _edit_queue(tmp_path, config):
    sent: list[dict[str, object]] = []
    edited: list[dict[str, object]] = []
    published: list[object] = []

    class Bot:
        async def send_message(self, chat_id, text, **kwargs):
            sent.append({"chat_id": chat_id, "text": text, **kwargs})
            return SimpleNamespace(message_id=21)

        async def edit_message_text(self, text, **kwargs):
            edited.append({"text": text, **kwargs})
            return SimpleNamespace(message_id=kwargs.get("message_id"))

        async def edit_message_caption(self, **kwargs):
            edited.append(kwargs)
            return SimpleNamespace(message_id=kwargs.get("message_id"))

    class Publisher:
        async def publish_now(self, item, **kwargs):
            published.append(item)
            return [1]

    db = Database(tmp_path / "edit.sqlite")
    db.init()
    preview_id = db.create_preview(
        donor="sample",
        source_message_ids=[3],
        log_chat_id="-1001234567890",
        text="Готовый текст",
        dedupe_text="готовый текст",
    )
    db.attach_preview_message(
        preview_id,
        log_message_id=50,
        content_message_id=50,
        kind="text",
    )
    queue = ReviewQueue(Bot(), config, db, Publisher(), SimpleNamespace())
    return queue, db, preview_id, sent, edited, published


def _reply(chat_id, chat_type, user_id, text, reply_id):
    async def answer(body):
        return SimpleNamespace(message_id=90, text=body)

    return SimpleNamespace(
        chat=SimpleNamespace(id=chat_id, type=chat_type),
        from_user=None if user_id is None else SimpleNamespace(id=user_id),
        text=text,
        reply_to_message=SimpleNamespace(message_id=reply_id),
        answer=answer,
    )


def test_stale_edit_callback_replies_in_the_log_and_does_not_publish(tmp_path):
    raw = yaml.safe_load((Path(__file__).resolve().parents[1] / "config.example.yaml").read_text())
    config = parse_config(raw)
    queue, db, preview_id, sent, edited, published = _edit_queue(tmp_path, config)

    class Query:
        def __init__(self, data: str) -> None:
            self.data = data
            self.from_user = SimpleNamespace(id=config.owner_id)

        async def answer(self, text=None, **kwargs):
            raise TelegramBadRequest(
                method=AnswerCallbackQuery(callback_query_id="1"),
                message="query is too old",
            )

    asyncio.run(queue.on_callback(Query(pack_callback("edit", preview_id))))
    assert published == []
    assert edited == []
    assert len(sent) == 1
    assert sent[0]["chat_id"] == -1001234567890
    assert sent[0]["chat_id"] != config.owner_id
    assert sent[0]["text"] == EDIT_HINT
    assert sent[0]["reply_to_message_id"] == 50
    assert "Превью" not in str(sent[0]["text"])
    assert db.pending_edit_prompts() == [(preview_id, 21)]
    assert db.get_preview(preview_id).state == "pending"

    db.transition_preview(preview_id, "rejected", expect="pending")
    closed_id = asyncio.run(deliver_edit_prompt(queue.bot, Query("e:1"), db, preview_id))
    assert closed_id == 21
    assert sent[-1]["chat_id"] == -1001234567890
    assert sent[-1]["text"] == "Это превью уже закрыто."
    assert sent[-1]["reply_to_message_id"] == 50
    assert published == []


def test_owner_log_reply_replaces_preview_and_keeps_buttons(tmp_path):
    raw = yaml.safe_load((Path(__file__).resolve().parents[1] / "config.example.yaml").read_text())
    config = parse_config(raw)
    queue, db, preview_id, sent, edited, published = _edit_queue(tmp_path, config)
    log_id = -1001234567890

    asyncio.run(
        queue.receive_edit(
            _reply(log_id, ChatType.CHANNEL, None, "Новый текст поста", 50)
        )
    )
    assert published == []
    assert db.get_preview(preview_id).text == "Новый текст поста"
    assert db.get_preview(preview_id).state == "pending"
    assert len(edited) == 1
    buttons = [
        button.text
        for row in edited[0]["reply_markup"].inline_keyboard
        for button in row
    ]
    assert buttons == ["Отправить", "Редактировать", "Отклонить"]

    asyncio.run(
        queue.receive_edit(
            _reply(log_id, ChatType.SUPERGROUP, 2, "Чужой текст", 50)
        )
    )
    asyncio.run(
        queue.receive_edit(
            _reply(config.owner_id, ChatType.PRIVATE, config.owner_id, "Личный текст", 50)
        )
    )
    assert db.get_preview(preview_id).text == "Новый текст поста"
    assert published == []
    assert all(item["chat_id"] != config.owner_id for item in sent)


def test_config_allows_empty_donors_and_numeric_log_channel():
    raw = yaml.safe_load((Path(__file__).resolve().parents[1] / "config.example.yaml").read_text())
    raw["donors"] = []
    raw.pop("signatures")
    raw["log"] = {"channel": -1001234567890}
    config = parse_config(raw)
    assert config.donors == ()
    assert config.signatures.templates == {}
    assert config.log_channel == "-1001234567890"
