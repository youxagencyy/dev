from newsbot.config import SignatureConfig
from newsbot.signatures import append_signature
from newsbot.textutil import fit_text


def _config() -> SignatureConfig:
    return SignatureConfig(
        default="channel",
        templates={
            "channel": "{channel}\n{hashtags}\n{channel_link}",
            "short": "Коротко {channel}",
        },
        channel_link="https://t.me/your_news",
        hashtags="#новости",
        channel_title="Новости",
    )


def test_default_template_fills_placeholders():
    result = append_signature("Текст новости", _config())
    assert result == "Текст новости\n\nНовости\n#новости\nhttps://t.me/your_news"
    assert "{channel}" not in result


def test_named_template():
    result = append_signature("Текст", _config(), "short")
    assert result == "Текст\n\nКоротко Новости"


def test_unknown_template_falls_back_to_default():
    result = append_signature("Текст", _config(), "missing")
    assert result.endswith("Новости\n#новости\nhttps://t.me/your_news")


def test_append_is_idempotent():
    once = append_signature("Текст новости", _config())
    assert append_signature(once, _config()) == once


def test_empty_body_is_just_the_footer():
    assert append_signature("  ", _config()) == "Новости\n#новости\nhttps://t.me/your_news"


def test_long_body_keeps_footer_inside_caption_limit():
    body = "слово " * 400
    signed = append_signature(body, _config())
    fitted = fit_text(signed, 1024)
    assert len(fitted) <= 1024
    assert fitted.endswith("Новости\n#новости\nhttps://t.me/your_news")
