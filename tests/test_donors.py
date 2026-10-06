from pathlib import Path

import yaml

from newsbot.config import Donor, load_config
from newsbot.donors import (
    add_donor,
    apply_donor_action,
    delete_donor,
    donors_keyboard,
    edit_keyboard,
    format_donor_list,
    pack_donor_callback,
    parse_donor_callback,
    parse_donor_ref,
    reject_donor_chat,
    rename_donor,
    save_donor_list,
    set_donor_enabled,
    DonorRefError,
)

SAMPLE = """
target:
  channel: "@your_news"
owner_id: 42
log:
  channel: "-1001234567890"
donors: []
signatures:
  default: channel
  channel_title: "Новости"
  channel_link: "https://t.me/your_news"
  hashtags: "#новости"
  templates:
    channel: "{channel}"
    short: "{channel_link}"
ad_filter:
  min_hits: 1
  max_external_links: 4
  keywords:
    - "реклама"
  regex:
    - '(?i)\\berid\\s*[:=]'
strip:
  patterns: []
  trailing_markers: []
links:
  strip_params: []
  domain_rewrite: {}
  blacklist_domains: []
rewrite:
  enabled: false
  tone: "нейтральный новостной"
  max_length: 900
  keep_media_captions: true
  temperature: 0.2
  system_prompt: "Только факты."
dedupe:
  window_hours: 24
  similarity_threshold: 0.72
  min_tokens: 6
rate_limit:
  min_interval_seconds: 3
  max_posts_per_hour: 30
"""


def test_parse_username_and_public_links():
    assert parse_donor_ref("@Sample_News") == "Sample_News"
    assert parse_donor_ref("sample_news") == "sample_news"
    assert parse_donor_ref("https://t.me/sample_news") == "sample_news"
    assert parse_donor_ref("http://t.me/sample_news/123") == "sample_news"
    assert parse_donor_ref("t.me/s/sample_news") == "sample_news"
    assert parse_donor_ref("https://telegram.me/sample_news?single") == "sample_news"


def test_parse_rejects_private_links():
    for raw in (
        "https://t.me/+AbCdEfGh",
        "https://t.me/joinchat/AbCdEfGh",
        "https://t.me/c/123456/7",
        "tg://join?invite=AbCdEfGh",
        "",
        "не канал",
    ):
        try:
            parse_donor_ref(raw)
        except DonorRefError:
            continue
        raise AssertionError(raw)


def test_reject_private_chats_and_groups():
    assert reject_donor_chat("channel") is None
    assert "Личные" in (reject_donor_chat("private") or "")
    assert "Группы" in (reject_donor_chat("group") or "")
    assert "Группы" in (reject_donor_chat("supergroup") or "")


def test_empty_list_is_one_line_and_offers_add():
    assert format_donor_list(()) == "Список доноров пуст."
    markup = donors_keyboard(())
    labels = [button.text for row in markup.inline_keyboard for button in row]
    assert labels == ["Добавить"]
    assert pack_donor_callback("add") == "dn:a"


def test_list_shows_state_and_per_donor_buttons():
    donors = (
        Donor("alpha_news", True, None),
        Donor("beta_news", False, "short"),
    )
    text = format_donor_list(donors)
    assert text == "@alpha_news — включён\n@beta_news — выключен"
    markup = donors_keyboard(donors)
    labels = [button.text for row in markup.inline_keyboard for button in row]
    assert labels == ["Добавить", "Удалить", "Редактировать", "Удалить", "Редактировать"]
    for row in markup.inline_keyboard:
        for button in row:
            assert button.callback_data is not None
            assert len(button.callback_data.encode("utf-8")) <= 64


def test_callback_data_stays_within_64_bytes():
    username = "a" + ("b" * 31)
    data = pack_donor_callback("confirm_delete", username)
    assert len(data.encode("utf-8")) <= 64
    assert parse_donor_callback(data) == ("confirm_delete", username)
    assert parse_donor_callback("s:1") is None


def test_ask_delete_does_not_remove_until_confirm():
    donors = (Donor("alpha_news", True, "short"),)
    asked, error = apply_donor_action(donors, "ask_delete", "alpha_news")
    assert error is None
    assert asked == donors
    deleted, error = apply_donor_action(donors, "confirm_delete", "alpha_news")
    assert error is None
    assert deleted == ()


def test_add_edit_delete_keep_signature(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text(SAMPLE, encoding="utf-8")
    config = load_config(path)
    added, error = add_donor(config.donors, "Alpha_News")
    assert error is None
    added = (Donor(added[0].username, added[0].enabled, "short"),)
    renamed, error = rename_donor(added, "alpha_news", "Beta_News")
    assert error is None
    assert renamed[0].signature == "short"
    assert renamed[0].enabled is True
    toggled, error = set_donor_enabled(renamed, "Beta_News", False)
    assert error is None
    assert toggled[0] == Donor("Beta_News", False, "short")
    again, error = add_donor(toggled, "beta_news")
    assert error == "Такой донор уже есть."
    saved = save_donor_list(path, toggled)
    assert saved.owner_id == 42
    assert saved.target_channel == "@your_news"
    assert saved.donors == (Donor("Beta_News", False, "short"),)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert raw["donors"] == [{"username": "Beta_News", "enabled": False, "signature": "short"}]
    removed, error = delete_donor(saved.donors, "BETA_NEWS")
    assert error is None
    emptied = save_donor_list(path, removed)
    assert emptied.donors == ()
    assert emptied.log_channel == "-1001234567890"


def test_edit_keyboard_toggles_enabled_label():
    on = edit_keyboard(Donor("alpha_news", True))
    off = edit_keyboard(Donor("alpha_news", False))
    assert on.inline_keyboard[0][0].text == "Выключить"
    assert off.inline_keyboard[0][0].text == "Включить"
    assert parse_donor_callback(on.inline_keyboard[0][0].callback_data) == ("disable", "alpha_news")
    assert parse_donor_callback(off.inline_keyboard[0][0].callback_data) == ("enable", "alpha_news")
