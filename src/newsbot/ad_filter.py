from __future__ import annotations

from newsbot.config import AdFilterConfig, fold_keyword
from newsbot.textutil import URL_RE, fold


def external_link_count(text: str) -> int:
    return len(URL_RE.findall(text or ""))


def matching_keywords(text: str, keywords: tuple[str, ...]) -> list[str]:
    folded = fold(text)
    hits: list[str] = []
    for keyword in keywords:
        needle = fold_keyword(keyword)
        if needle and needle in folded:
            hits.append(keyword)
    return hits


def is_advertisement(text: str, config: AdFilterConfig) -> tuple[bool, str]:
    """Return whether the post is a pure ad, plus a short reason.

    Heuristic (no extra weighting):

    * distinct blocklist hits >= ``min_hits`` (casefold, ``ё`` == ``е``,
      substring, whitespace collapsed);
    * or http(s) link count > ``max_external_links``;
    * or any configured regular expression matches the original text.
    """
    if not (text or "").strip():
        return False, ""
    hits = matching_keywords(text, config.keywords)
    if config.keywords and len(hits) >= config.min_hits:
        shown = ", ".join(hits[:5])
        return True, f"ad keywords ({len(hits)}): {shown}"
    links = external_link_count(text)
    if links > config.max_external_links:
        return True, f"too many links: {links} > {config.max_external_links}"
    for pattern in config.patterns:
        if pattern.search(text):
            return True, f"ad regex: {pattern.pattern}"
    return False, ""
