import re

from newsbot.config import StripConfig
from newsbot.signatures import strip_donor_marks


def _config() -> StripConfig:
    return StripConfig(
        patterns=(
            re.compile(r"(?im)^\s*источник\s*[:—-].*(?:\n|$)"),
            re.compile(r"(?im)^\s*@[A-Za-z0-9_]{3,}\s*(?:\n|$)"),
        ),
        trailing_markers=("подписывайтесь", "наш телеграм"),
    )


def test_regex_removes_source_line_and_mention_line():
    text = "Главное событие дня.\nИсточник: РИА\n@donor_channel\nДальше по делу."
    assert strip_donor_marks(text, _config()) == "Главное событие дня.\nДальше по делу."


def test_trailing_marker_cuts_the_tail():
    text = "Событие дня в городе.\n\nПодписывайтесь на канал\nпромо и ссылки"
    assert strip_donor_marks(text, _config()) == "Событие дня в городе."


def test_marker_is_case_insensitive():
    text = "Текст новости.\nПОДПИСЫВАЙТЕСЬ"
    assert strip_donor_marks(text, _config()) == "Текст новости."


def test_body_without_markers_stays():
    text = "Коротко: заседание перенесли на пятницу."
    assert strip_donor_marks(text, _config()) == text
