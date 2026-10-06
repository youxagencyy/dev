import asyncio
from pathlib import Path
from types import SimpleNamespace

import yaml
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import AnswerCallbackQuery

from newsbot.branches import (
    add_branch,
    branches_keyboard,
    format_current_donors,
    format_template,
    pack_branch_callback,
    parse_branch_callback,
    parse_destination,
    save_branches,
    select_branch,
    set_branch_template,
    template_keyboard,
    DestinationError,
)
from newsbot.commands import ADD_DONOR_PROMPT, build_router, deliver_add_prompt
from newsbot.config import Donor, parse_config
from newsbot.db import Database
from newsbot.donors import donors_keyboard, save_donor_list
from newsbot.review import preview_label, preview_publish_channel
from newsbot.review_queue import build_review_router
from newsbot.runtime import Runtime
from tests.test_donors import SAMPLE

ROOT = Path(__file__).resolve().parents[1]


def _two_feeds() -> dict:
    raw = yaml.safe_load(SAMPLE)
    raw["branches"] = [
        {
            "name": "Новости",
            "publish": "@your_news",
            "review": "-1001234567890",
            "donors": [{"username": "sample_donor", "enabled": True}],
        },
        {
            "name": "Крипто",
            "publish": "@crypto_out",
            "review": "-1001234567890",
            "donors": [{"username": "btc_feed", "enabled": True, "signature": "short"}],
        },
    ]
    raw["current_branch"] = "Новости"
    return raw


def test_legacy_config_becomes_news_branch():
    config = parse_config(yaml.safe_load(SAMPLE))
    assert config.current_branch == "Новости"
    assert config.branches[0].name == "Новости"
    assert config.branches[0].publish_channel == config.target_channel == "@your_news"
    assert config.branches[0].review_channel == config.log_channel
    assert config.branches[0].donors == ()


def test_switch_branch_changes_donors_and_publish_channel():
    config = parse_config(_two_feeds())
    assert [donor.username for donor in config.donors] == ["sample_donor"]
    switched, error = select_branch(config, 1)
    assert error is None
    assert switched.current_branch == "Крипто"
    assert switched.target_channel == "@crypto_out"
    assert [donor.username for donor in switched.donors] == ["btc_feed"]
    assert switched.donors[0].signature == "short"
    assert switched.log_channel == "-1001234567890"
    news = switched.branches[0]
    assert news.name == "Новости"
    assert [donor.username for donor in news.donors] == ["sample_donor"]


def test_branch_buttons_name_the_feed_and_stay_within_64_bytes():
    config = parse_config(_two_feeds())
    markup = branches_keyboard(config)
    labels = [button.text for row in markup.inline_keyboard for button in row]
    assert labels[0] == "✓ Новости"
    assert labels[1] == "Крипто"
    assert "Куда публиковать" in labels
    assert "Канал проверки" in labels
    assert labels[-1] == "Добавить ветку"
    for row in markup.inline_keyboard:
        for button in row:
            assert button.callback_data is not None
            assert len(button.callback_data.encode("utf-8")) <= 64
    assert parse_branch_callback(pack_branch_callback("switch", 1)) == ("switch", 1)
    assert parse_branch_callback(pack_branch_callback("add")) == ("add", None)
    assert parse_branch_callback(pack_branch_callback("publish")) == ("publish", None)
    assert parse_branch_callback("dn:a") is None


def test_donor_row_labels_include_the_channel():
    markup = donors_keyboard((Donor("alpha_news", True), Donor("beta_news", False)))
    assert [button.text for button in markup.inline_keyboard[1]] == [
        "Удалить @alpha_news",
        "Редактировать @alpha_news",
    ]
    assert [button.text for button in markup.inline_keyboard[2]] == [
        "Удалить @beta_news",
        "Редактировать @beta_news",
    ]


def test_add_branch_may_reuse_review_channel(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(_two_feeds(), allow_unicode=True), encoding="utf-8")
    config = parse_config(_two_feeds())
    added, error = add_branch(config, "Крипто", "@other", config.log_channel)
    assert error == "Ветка с таким названием уже есть."
    added, error = add_branch(config, "Город", "@city_out", config.log_channel)
    assert error is None
    assert added.current_branch == "Город"
    assert added.log_channel == config.log_channel
    assert added.donors == ()
    saved = save_branches(path, added)
    assert saved.current_branch == "Город"
    assert [branch.name for branch in saved.branches] == ["Новости", "Крипто", "Город"]
    assert saved.branches[1].donors[0].username == "btc_feed"
    disk = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert disk["branches"][0]["donors"][0]["username"] == "sample_donor"
    assert disk["target"]["channel"] == "@city_out"


def test_donor_edit_updates_only_the_current_branch(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(_two_feeds(), allow_unicode=True), encoding="utf-8")
    config = parse_config(yaml.safe_load(path.read_text(encoding="utf-8")))
    saved = save_donor_list(path, (Donor("alpha_news", True, None),))
    assert [donor.username for donor in saved.donors] == ["alpha_news"]
    assert saved.branches[1].donors[0].username == "btc_feed"
    text = format_current_donors(saved)
    assert text.startswith("Ветка: Новости")
    assert "@alpha_news" in text
    assert "btc_feed" not in text


def test_destination_accepts_username_and_numeric_id():
    assert parse_destination("@City_News") == "@City_News"
    assert parse_destination("https://t.me/city_news/3") == "@city_news"
    assert parse_destination("-1001234567890") == "-1001234567890"
    for raw in ("https://t.me/+AbCdEfGh", "https://t.me/c/123/4", "не канал", ""):
        try:
            parse_destination(raw)
        except DestinationError:
            continue
        raise AssertionError(raw)


def test_preview_is_labeled_and_publishes_to_its_own_channel(tmp_path: Path):
    assert preview_label("Крипто", "Биткоин вырос") == "Ветка: Крипто\n\nБиткоин вырос"
    assert preview_label("", "Текст").startswith("Ветка: Новости")
    assert preview_publish_channel("@crypto_out", "@your_news") == "@crypto_out"
    assert preview_publish_channel("", "@your_news") == "@your_news"
    db = Database(tmp_path / "previews.sqlite")
    db.init()
    preview_id = db.create_preview(
        donor="btc_feed",
        source_message_ids=[9],
        log_chat_id="-1001234567890",
        text="Биткоин вырос",
        dedupe_text="биткоин вырос",
        branch_name="Крипто",
        target_channel="@crypto_out",
    )
    preview = db.get_preview(preview_id)
    assert preview is not None
    assert preview.branch_name == "Крипто"
    assert preview.target_channel == "@crypto_out"
    assert "Ветка: Крипто" not in preview.text


def test_stale_add_callback_still_asks_for_a_channel():
    sent: dict[str, object] = {}

    class Bot:
        async def send_message(self, chat_id, text, **kwargs):
            sent["chat_id"] = chat_id
            sent["text"] = text
            return SimpleNamespace(message_id=15)

    class Query:
        async def answer(self, text=None, **kwargs):
            raise TelegramBadRequest(
                method=AnswerCallbackQuery(callback_query_id="1"),
                message="query is too old",
            )

    runtime = Runtime(parse_config(yaml.safe_load(SAMPLE)), None, None, None, None)
    message_id = asyncio.run(deliver_add_prompt(Bot(), 7, Query(), runtime))
    assert message_id == 15
    assert sent["chat_id"] == 7
    assert sent["text"] == ADD_DONOR_PROMPT
    assert runtime.donor_prompt is not None
    assert runtime.donor_prompt.kind == "add"


def test_review_router_does_not_claim_donor_callbacks():
    runtime = Runtime(parse_config(yaml.safe_load(SAMPLE)), None, None, None, None)
    commands = build_router(runtime, SimpleNamespace())
    review = build_review_router(SimpleNamespace(config=runtime.config))
    command_names = [handler.callback.__name__ for handler in commands.callback_query.handlers]
    assert "donor_callback" in command_names
    assert "branch_callback" in command_names

    async def check(data: str) -> bool:
        query = SimpleNamespace(data=data)
        handler = review.callback_query.handlers[0]
        return await handler.check(query)

    assert asyncio.run(check("s:1"))[0] is True
    assert asyncio.run(check("dn:a"))[0] is False
    assert asyncio.run(check("br:a"))[0] is False
    assert asyncio.run(check("tm:e"))[0] is False


def test_template_is_per_branch_and_empty_text_clears_it(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(_two_feeds(), allow_unicode=True), encoding="utf-8")
    config = parse_config(_two_feeds())
    updated = set_branch_template(config, "Наш канал\nhttps://t.me/your_news")
    assert updated.branches[0].template.startswith("Наш канал")
    assert updated.branches[1].template == ""
    saved = save_branches(path, updated)
    assert saved.branches[0].template.startswith("Наш канал")
    cleared = save_branches(path, set_branch_template(saved, "  "))
    assert cleared.branches[0].template == ""
    assert format_template(cleared).endswith("Шаблон пуст.")
    labels = [button.text for row in template_keyboard().inline_keyboard for button in row]
    assert labels == ["Изменить", "Очистить"]
    disk = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert disk["branches"][1]["donors"][0]["username"] == "btc_feed"


def test_empty_ad_list_still_drops_default_phrases():
    raw = yaml.safe_load(SAMPLE)
    raw["ad_filter"]["keywords"] = []
    config = parse_config(raw)
    assert "реклама" in config.ad_filter.keywords
    assert "erid" in config.ad_filter.keywords
    assert "промокод" in config.ad_filter.keywords
    assert any("партн" in item for item in config.ad_filter.keywords)


def test_example_config_file_is_the_news_branch():
    raw = yaml.safe_load((ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    config = parse_config(raw)
    assert config.current_branch == "Новости"
    assert config.branches[0].publish_channel == "@your_news"
