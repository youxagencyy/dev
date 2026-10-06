import asyncio

import httpx

from newsbot.config import RewriteConfig
from newsbot.db import Database
from newsbot.dedupe import Deduper
from newsbot.pipeline import Pipeline, PostInput
from newsbot.rewrite import Rewriter
from tests.helpers import make_config


class FakeRewriter:
    def __init__(self, *, active: bool = True, fail: bool = False) -> None:
        self.active = active
        self.fail = fail
        self.calls = 0

    async def rewrite(self, text: str) -> tuple[str, str | None]:
        self.calls += 1
        if self.fail:
            return text, "timeout"
        return f"{text} [ред.]", None


def _pipeline(tmp_path, rewriter, config=None):
    db = Database(tmp_path / "bot.sqlite")
    db.init()
    cfg = config or make_config()
    return Pipeline(cfg, db, Deduper(db, cfg.dedupe), rewriter), db


def _post(text: str, **kwargs) -> PostInput:
    params = {
        "donor": "sample_donor",
        "message_id": 1,
        "text": text,
        "is_service": False,
        "has_photo": False,
    }
    params.update(kwargs)
    return PostInput(**params)


def test_skips_service_empty_and_ads(tmp_path):
    rewriter = FakeRewriter()
    pipeline, _db = _pipeline(tmp_path, rewriter)
    service = asyncio.run(pipeline.run(_post("", is_service=True), record=True))
    empty = asyncio.run(pipeline.run(_post("   "), record=True))
    ad = asyncio.run(pipeline.run(_post("Промокод внутри поста"), record=True))
    assert service.action == "skip" and service.reason == "service"
    assert empty.action == "skip" and empty.reason == "empty"
    assert ad.action == "skip" and "промокод" in ad.reason
    assert rewriter.calls == 0


def test_cleans_links_strips_footer_and_appends_signature(tmp_path):
    rewriter = FakeRewriter(active=False)
    pipeline, _db = _pipeline(tmp_path, rewriter)
    text = (
        "Открыли станцию https://old.news/a?utm_source=tg&id=7\n"
        "Подписывайтесь на канал"
    )
    result = asyncio.run(pipeline.run(_post(text), record=True))
    assert result.action == "publish"
    assert "old.news" not in result.text
    assert "utm_" not in result.text
    assert "http" not in result.text.split("Новости")[0]
    assert "Подписывайтесь" not in result.text
    assert result.text.endswith("Новости\n#новости\nhttps://t.me/your_news")
    assert rewriter.calls == 0


def test_preview_does_not_block_later_publish(tmp_path):
    pipeline, _db = _pipeline(tmp_path, FakeRewriter(active=False))
    post = _post("Уникальная заметка про мост через реку")
    preview = asyncio.run(pipeline.run(post, record=False))
    published = asyncio.run(pipeline.run(post, record=True))
    again = asyncio.run(
        pipeline.run(_post("Уникальная заметка про мост через реку", message_id=2), record=True)
    )
    assert preview.action == "publish"
    assert published.action == "publish"
    assert again.action == "duplicate"


def test_llm_failure_falls_back_to_cleaned_text(tmp_path):
    pipeline, db = _pipeline(tmp_path, FakeRewriter(fail=True))
    result = asyncio.run(pipeline.run(_post("Событие без рекламы"), record=True))
    assert result.action == "publish"
    assert result.text.startswith("Событие без рекламы")
    assert "[ред.]" not in result.text
    assert db.recent_errors(1)[0].context == "rewrite"


def test_donor_signature_is_not_kept_and_branch_footer_is(tmp_path):
    pipeline, _db = _pipeline(tmp_path, FakeRewriter(active=False))
    named = asyncio.run(pipeline.run(_post("Событие без рекламы", signature_template="short"), record=True))
    assert "Коротко" not in named.text
    assert named.text.endswith("https://t.me/your_news")
    custom = asyncio.run(
        pipeline.run(
            _post(
                "Другое событие без рекламы https://donor.example/a\n@donor_channel",
                message_id=2,
                footer="Наш канал\nhttps://t.me/your_news",
            ),
            record=True,
        )
    )
    assert custom.action == "publish"
    assert "donor.example" not in custom.text
    assert "@donor_channel" not in custom.text
    assert custom.text.endswith("Наш канал\nhttps://t.me/your_news")
    assert "Новости\n#новости" not in custom.text


def test_empty_body_after_cleaning_is_skipped(tmp_path):
    pipeline, _db = _pipeline(tmp_path, FakeRewriter(active=False))
    result = asyncio.run(
        pipeline.run(_post("https://t.me/donor_news\nПодписывайтесь"), record=True)
    )
    assert result.action == "skip"
    assert result.reason == "empty_after_clean"


def test_inactive_rewriter_is_not_called(tmp_path):
    rewriter = FakeRewriter(active=False)
    pipeline, _db = _pipeline(tmp_path, rewriter)
    result = asyncio.run(pipeline.run(_post("Событие без рекламы"), record=True))
    assert rewriter.calls == 0
    assert result.text.startswith("Событие без рекламы")


def test_rewriter_without_key_does_not_touch_network():
    def explode(request: httpx.Request) -> httpx.Response:
        raise AssertionError(request.url)

    config = make_config(
        rewrite=RewriteConfig(
            enabled=True,
            tone="нейтральный",
            max_length=100,
            keep_media_captions=True,
            system_prompt="не выдумывай",
            temperature=0,
        )
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(explode))
    rewriter = Rewriter(config.rewrite, api_key="", base_url="https://example.invalid/v1", model="x", client=client)
    assert rewriter.active is False

    async def check() -> None:
        text, error = await rewriter.rewrite("Факт")
        assert text == "Факт"
        assert error is None
        await client.aclose()

    asyncio.run(check())
