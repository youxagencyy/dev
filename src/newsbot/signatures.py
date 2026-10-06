from __future__ import annotations

import re

from newsbot.config import SignatureConfig, StripConfig
from newsbot.textutil import fold

PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def strip_donor_marks(text: str, config: StripConfig) -> str:
    """Drop donor watermarks and a trailing promo block.

    Each ``patterns`` entry is removed with ``re.sub``. Then, if a line
    contains any ``trailing_markers`` phrase (casefold), that line and
    everything after it is cut. Markers are meant for footer CTAs; a marker
    inside the news body will also cut the tail.
    """
    cleaned = text or ""
    for pattern in config.patterns:
        cleaned = pattern.sub("", cleaned)
    lines = cleaned.splitlines()
    cut = len(lines)
    for index, line in enumerate(lines):
        folded = fold(line)
        if any(marker in folded for marker in config.trailing_markers):
            cut = index
            break
    kept = "\n".join(lines[:cut])
    kept = re.sub(r"[ \t]+\n", "\n", kept)
    kept = re.sub(r"\n{3,}", "\n\n", kept)
    return kept.strip()


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
