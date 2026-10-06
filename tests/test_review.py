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
from newsbot.review_queue import EDIT_PROMPT, ReviewQueue, deliver_edit_prompt


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


def test_stale_edit_callback_asks_for_text_and_does_not_publish(tmp_path):
    sent: dict[str, object] = {}
    published: list[object] = []

    class Bot:
        async def send_message(self, chat_id, text, **kwargs):
            sent["chat_id"] = chat_id
            sent["text"] = text
            return SimpleNamespace(message_id=21)

    class Query:
        def __init__(self, data: str) -> None:
            self.data = data
            self.from_user = SimpleNamespace(id=123456789)

        async def answer(self, text=None, **kwargs):
            raise TelegramBadRequest(
                method=AnswerCallbackQuery(callback_query_id="1"),
                message="query is too old",
            )

    class Publisher:
        async def publish_now(self, item, **kwargs):
            published.append(item)
            return [1]

    raw = yaml.safe_load((Path(__file__).resolve().parents[1] / "config.example.yaml").read_text())
    config = parse_config(raw)
    db = Database(tmp_path / "edit.sqlite")
    db.init()
    preview_id = db.create_preview(
        donor="sample",
        source_message_ids=[3],
        log_chat_id="-1001234567890",
        text="Готовый текст",
        dedupe_text="готовый текст",
    )
    queue = ReviewQueue(Bot(), config, db, Publisher(), SimpleNamespace())
    message_id = asyncio.run(
        queue.on_callback(Query(pack_callback("edit", preview_id)))
    )
    assert message_id is None
    assert published == []
    assert sent["chat_id"] == config.owner_id
    text = str(sent["text"])
    assert text == f"Превью {preview_id}. {EDIT_PROMPT}"
    assert "Ответьте" in text
    assert "Отправить" in text
    assert "Редактировать" in text
    assert "Отклонить" in text
    assert "не уйдёт" in text
    assert db.pending_edit_prompts() == [(preview_id, 21)]
    assert db.get_preview(preview_id).state == "pending"

    closed = asyncio.run(deliver_edit_prompt(Bot(), config.owner_id, Query("e:1"), db, preview_id))
    assert closed == 21
    db.transition_preview(preview_id, "rejected", expect="pending")
    sent.clear()
    closed_id = asyncio.run(
        deliver_edit_prompt(Bot(), config.owner_id, Query("e:1"), db, preview_id)
    )
    assert closed_id == 21
    assert sent["text"] == "Это превью уже закрыто."
    assert published == []


def test_config_allows_empty_donors_and_numeric_log_channel():
    raw = yaml.safe_load((Path(__file__).resolve().parents[1] / "config.example.yaml").read_text())
    raw["donors"] = []
    raw.pop("signatures")
    raw["log"] = {"channel": -1001234567890}
    config = parse_config(raw)
    assert config.donors == ()
    assert config.signatures.templates == {}
    assert config.log_channel == "-1001234567890"
