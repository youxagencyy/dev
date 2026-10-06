from __future__ import annotations

import re

from newsbot.config import SignatureConfig, StripConfig
from newsbot.textutil import fold

PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

# Applied even when config.yaml has no strip section. A matching line is removed.
# A short CTA in the footer also drops everything after it.
_BUILTIN_LINE_PATTERNS = (
    re.compile(r"(?im)^[^\S\n]*[@#]?(?:источник|джерело)\s*[:—\-].*(?:\n|$)"),
    re.compile(r"(?im)^[^\S\n]*@[A-Za-z][A-Za-z0-9_]{3,31}[^\S\n]*(?:\n|$)"),
    re.compile(
        r"(?im)^[^\S\n]*(?:https?://)?(?:t\.me|telegram\.me)/\S+[^\S\n]*(?:\n|$)"
    ),
    re.compile(
        r"(?im)^(?:[ \t]|[^\w\s]){0,12}(?:подпис\w*|підпис\w*|пидпис\w*)\b.*(?:\n|$)"
    ),
    re.compile(r"(?im)^[^\S\n]*наш(?:е|а)?\s+(?:канал|телеграм|джерело)\b.*(?:\n|$)"),
)
_BUILTIN_TAIL_MARKERS = (
    "подписывайся",
    "подписывайтесь",
    "подпишись",
    "подпишитесь",
    "подписаться",
    "підписуйся",
    "підписуйтесь",
    "підпишись",
    "підпишитесь",
    "підписатися",
    "наш канал",
    "наш телеграм",
    "наше джерело",
)
_TAIL_LINE_LIMIT = 100


def strip_donor_marks(text: str, config: StripConfig) -> str:
    """Drop donor watermarks and a trailing promo block.

    Built-in lines (a lone ``@username``, a ``t.me`` line, «источник:»,
    «подписывайся» / «підпишись», «наш канал») are removed even when the
    yaml list is empty. Configured ``patterns`` are removed the same way.
    A short CTA in the footer — after a blank line, or in the last lines —
    drops that line and everything after it. The same cut uses
    ``trailing_markers`` from config.
    """
    lines = (text or "").splitlines()
    cut = _footer_cut(lines, config.trailing_markers)
    if cut is not None:
        lines = lines[:cut]
    cleaned = "\n".join(lines)
    if cleaned and not cleaned.endswith("\n"):
        cleaned += "\n"
    for pattern in (*_BUILTIN_LINE_PATTERNS, *config.patterns):
        cleaned = pattern.sub("", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _footer_cut(lines: list[str], extra_markers: tuple[str, ...]) -> int | None:
    """Index of the first footer CTA, if the match sits in the tail."""
    last_blank = None
    for index, line in enumerate(lines):
        if not line.strip():
            last_blank = index
    if last_blank is not None and 0 < last_blank < len(lines) - 1:
        for index in range(last_blank + 1, len(lines)):
            if _line_has_marker(lines[index], extra_markers):
                return index
    start = max(0, len(lines) - 4)
    for index in range(start, len(lines)):
        if _line_has_marker(lines[index], extra_markers):
            return index
    return None


def _line_has_marker(line: str, extra_markers: tuple[str, ...]) -> bool:
    folded = fold(line)
    if not folded or len(folded) > _TAIL_LINE_LIMIT:
        return False
    markers = _BUILTIN_TAIL_MARKERS + tuple(marker for marker in extra_markers if marker)
    return any(marker in folded for marker in markers)


def render_signature(config: SignatureConfig, template_name: str | None = None) -> str:
    name = template_name or config.default
    if name not in config.templates:
        name = config.default
    template = config.templates.get(name, "")
    values = {
        "channel_link": config.channel_link,
        "hashtags": config.hashtags,
        "channel": config.channel_title,
    }

    def replace(match: re.Match[str]) -> str:
        return values.get(match.group(1), match.group(0))

    return PLACEHOLDER_RE.sub(replace, template).strip()


def append_footer(text: str, footer: str) -> str:
    """Append the branch template. The donor's own signature is not used."""
    footer = (footer or "").strip()
    body = (text or "").rstrip()
    if not footer:
        return body
    if body == footer or body.endswith("\n\n" + footer):
        return body
    if not body:
        return footer
    return f"{body}\n\n{footer}"


def append_signature(
    text: str,
    config: SignatureConfig,
    template_name: str | None = None,
) -> str:
    footer = render_signature(config, template_name)
    body = (text or "").rstrip()
    if not footer:
        return body
    if body == footer or body.endswith("\n\n" + footer):
        return body
    if not body:
        return footer
    return f"{body}\n\n{footer}"
