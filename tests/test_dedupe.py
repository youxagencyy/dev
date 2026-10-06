from datetime import timedelta

from newsbot.db import Database, utcnow
from newsbot.dedupe import Deduper, jaccard
from newsbot.textutil import content_tokens, normalize_for_fingerprint
from tests.helpers import make_config


def _deduper(tmp_path, **kwargs) -> Deduper:
    db = Database(tmp_path / "dedupe.sqlite")
    db.init()
    config = make_config().dedupe
    if kwargs:
        config = type(config)(
            window_hours=kwargs.get("window_hours", config.window_hours),
            similarity_threshold=kwargs.get("similarity_threshold", config.similarity_threshold),
            min_tokens=kwargs.get("min_tokens", config.min_tokens),
        )
    return Deduper(db, config)


def test_exact_duplicate_inside_window(tmp_path):
    deduper = _deduper(tmp_path)
    text = "Пожар в порту"
    deduper.remember(text, donor="a", message_id=1)
    duplicate, reason = deduper.is_duplicate("Пожар, в порту!")
    assert duplicate
    assert reason == "exact fingerprint"


def test_same_story_outside_window_is_new(tmp_path):
    deduper = _deduper(tmp_path, window_hours=24)
    text = "Пожар в порту"
    deduper.remember(text, donor="a", message_id=1, now=utcnow() - timedelta(hours=48))
    duplicate, _reason = deduper.is_duplicate(text, now=utcnow())
    assert duplicate is False


def test_similar_story_from_another_donor(tmp_path):
    left = "правительство региона сообщило о запуске новой программы поддержки семей с детьми в этом году"
    right = "правительство региона сообщило о старте новой программы поддержки семей с детьми в этом году"
    score = jaccard(
        content_tokens(normalize_for_fingerprint(left)),
        content_tokens(normalize_for_fingerprint(right)),
    )
    assert score >= 0.72
    deduper = _deduper(tmp_path)
    deduper.remember(left, donor="ria", message_id=10)
    duplicate, reason = deduper.is_duplicate(right)
    assert duplicate
    assert reason.startswith("similar")


def test_different_story_is_not_similar(tmp_path):
    left = "правительство региона сообщило о запуске новой программы поддержки семей с детьми в этом году"
    right = "центробанк повысил ключевую ставку после заседания совета директоров в пятницу утром"
    score = jaccard(
        content_tokens(normalize_for_fingerprint(left)),
        content_tokens(normalize_for_fingerprint(right)),
    )
    assert score < 0.72
    deduper = _deduper(tmp_path)
    deduper.remember(left, donor="ria", message_id=10)
    assert deduper.is_duplicate(right)[0] is False


def test_short_text_matches_only_exactly(tmp_path):
    deduper = _deduper(tmp_path)
    deduper.remember("Дождь в Сочи", donor="a", message_id=1)
    assert deduper.is_duplicate("Снег в Сочи")[0] is False
    assert deduper.is_duplicate("Дождь в Сочи")[0] is True


def test_urls_and_case_do_not_change_fingerprint(tmp_path):
    deduper = _deduper(tmp_path)
    deduper.remember(
        "Привет мир https://example.com/a?utm_source=tg",
        donor="a",
        message_id=1,
    )
    assert deduper.is_duplicate("привет, мир!")[0] is True
