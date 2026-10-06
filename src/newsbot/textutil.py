from __future__ import annotations

import re

# Plain-text URLs. Trailing punctuation is peeled off by the link rewriter.
URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
INVISIBLE_RE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")
WORD_RE = re.compile(r"[0-9a-zа-яё]+", re.IGNORECASE)


def fold(text: str) -> str:
    """Casefold and normalize yo so phrase lists stay predictable."""
    collapsed = INVISIBLE_RE.sub("", text or "")
    collapsed = collapsed.casefold().replace("ё", "е")
    return re.sub(r"\s+", " ", collapsed).strip()


def prepare_text(text: str) -> str:
    return INVISIBLE_RE.sub("", text or "").strip()


def normalize_for_fingerprint(text: str) -> str:
    """Lowercase words only: URLs, punctuation, and yo/е differences drop out."""
    without_urls = URL_RE.sub(" ", prepare_text(text))
    words = WORD_RE.findall(without_urls.lower().replace("ё", "е"))
    return " ".join(words)


def content_tokens(normalized: str) -> set[str]:
    return {word for word in normalized.split() if len(word) >= 3}


def fit_text(text: str, limit: int) -> str:
    """Trim to a Telegram limit, keeping the last paragraph (the signature) when it fits."""
    text = (text or "").strip()
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if "\n\n" in text:
        body, footer = text.rsplit("\n\n", 1)
        footer = footer.strip()
        separator = 2
        if footer and len(footer) + separator < limit:
            room = limit - len(footer) - separator
            body = body.strip()
            if len(body) > room:
                ellipsis = "…"
                body = body[: max(0, room - len(ellipsis))].rstrip() + ellipsis
            if body:
                return f"{body}\n\n{footer}"
            return footer[:limit]
    ellipsis = "…"
    if limit == 1:
        return ellipsis
    return text[: limit - len(ellipsis)].rstrip() + ellipsis
