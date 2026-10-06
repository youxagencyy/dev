from newsbot.config import LinkConfig
from newsbot.links import rewrite_links


def _config() -> LinkConfig:
    return LinkConfig(
        strip_params=frozenset({"fbclid", "yclid"}),
        domain_rewrite={"old.news": "new.news"},
        blacklist_domains=frozenset({"ads.example"}),
    )


def test_strips_utm_and_tracking_params_and_rewrites_domain():
    text = "Смотрите https://old.news/a?utm_source=tg&id=5&fbclid=abc."
    result = rewrite_links(text, _config())
    assert result == "Смотрите https://new.news/a?id=5."
    assert "utm_" not in result
    assert "fbclid" not in result


def test_utm_is_stripped_even_when_not_listed():
    config = LinkConfig(strip_params=frozenset(), domain_rewrite={}, blacklist_domains=frozenset())
    result = rewrite_links("https://example.com/x?utm_campaign=1&ok=2", config)
    assert result == "https://example.com/x?ok=2"


def test_www_host_matches_rewrite_and_blacklist():
    text = "A https://www.old.news/p B https://www.ads.example/banner тут"
    result = rewrite_links(text, _config())
    assert "https://new.news/p" in result
    assert "ads.example" not in result
    assert result.endswith("тут")


def test_keeps_fragment_and_balanced_parentheses():
    config = LinkConfig(strip_params=frozenset(), domain_rewrite={}, blacklist_domains=frozenset())
    text = "Статья https://ru.wikipedia.org/wiki/Москва_(город)#История."
    assert rewrite_links(text, config) == text


def test_text_without_urls_is_unchanged():
    config = _config()
    assert rewrite_links("Просто текст новости.", config) == "Просто текст новости."
