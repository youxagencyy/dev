import re

from newsbot.ad_filter import is_advertisement
from newsbot.config import AdFilterConfig


def _config(**kwargs) -> AdFilterConfig:
    params = {
        "keywords": ("реклама", "erid", "промокод", "партнёрский материал"),
        "min_hits": 1,
        "max_external_links": 3,
        "patterns": (),
    }
    params.update(kwargs)
    return AdFilterConfig(**params)


def test_news_is_not_an_ad():
    text = "В Москве открыли новую станцию метро на севере города."
    assert is_advertisement(text, _config()) == (False, "")


def test_keyword_hit_is_case_insensitive():
    is_ad, reason = is_advertisement("Срочно: РеКлАмА банка", _config())
    assert is_ad
    assert "реклама" in reason


def test_yo_and_spacing_do_not_hide_a_phrase():
    is_ad, reason = is_advertisement("Партнерский   материал о креме", _config())
    assert is_ad
    assert "партнёрский материал" in reason


def test_min_hits_requires_enough_phrases():
    text = "В материале один раз сказано: реклама как отрасль выросла."
    assert is_advertisement(text, _config(min_hits=2))[0] is False
    both = "реклама и промокод в одном посте"
    assert is_advertisement(both, _config(min_hits=2))[0] is True


def test_too_many_external_links():
    links = " ".join(f"https://example.com/{index}" for index in range(3))
    assert is_advertisement(f"Обзор {links}", _config(keywords=()))[0] is False
    links = " ".join(f"https://example.com/{index}" for index in range(4))
    is_ad, reason = is_advertisement(f"Обзор {links}", _config(keywords=()))
    assert is_ad
    assert "too many links" in reason


def test_optional_regex():
    pattern = re.compile(r"(?i)\berid\s*[:=]")
    text = "Маркировка ERID: LatgB123 в карточке"
    assert is_advertisement(text, _config(keywords=(), patterns=(pattern,)))[0] is True
    assert is_advertisement("Обычная заметка", _config(keywords=(), patterns=(pattern,)))[0] is False


def test_empty_text_is_not_an_ad():
    assert is_advertisement("  ", _config()) == (False, "")
