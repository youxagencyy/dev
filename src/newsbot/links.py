from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from newsbot.config import LinkConfig
from newsbot.textutil import URL_RE

TRAILING = ".,;:!?)]}>\"'"


def rewrite_links(text: str, config: LinkConfig) -> str:
    """Normalize URLs inside plain text.

    * Query keys that start with ``utm_`` are always removed.
    * Keys listed in ``strip_params`` are removed (case-insensitive).
    * ``domain_rewrite`` replaces the host (``www.`` is ignored on lookup).
    * Hosts in ``blacklist_domains`` are deleted from the text.
    Other query parameters, the path, and the fragment stay.
    """
    if not text:
        return ""

    def replace(match: re.Match[str]) -> str:
        raw = match.group(0)
        url, trail = _split_trail(raw)
        rewritten = rewrite_url(url, config)
        if rewritten is None:
            return ""
        return rewritten + trail

    updated = URL_RE.sub(replace, text)
    updated = re.sub(r"[ \t]{2,}", " ", updated)
    updated = re.sub(r"\n{3,}", "\n\n", updated)
    return updated.strip()


def rewrite_url(url: str, config: LinkConfig) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return url
    host = _hostname(parsed.netloc)
    if host in config.blacklist_domains:
        return None
    new_host = config.domain_rewrite.get(host)
    netloc = _replace_host(parsed.netloc, new_host) if new_host else parsed.netloc
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    kept = [(key, value) for key, value in pairs if not _drop_param(key, config)]
    query = urlencode(kept, doseq=True)
    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, query, parsed.fragment))


def _drop_param(key: str, config: LinkConfig) -> bool:
    folded = key.casefold()
    return folded.startswith("utm_") or folded in config.strip_params


def _hostname(netloc: str) -> str:
    host = netloc.split("@")[-1].casefold()
    if host.startswith("["):
        return host
    host = host.split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host


def _replace_host(netloc: str, new_host: str) -> str:
    userinfo = ""
    hostport = netloc
    if "@" in netloc:
        userinfo, hostport = netloc.rsplit("@", 1)
        userinfo += "@"
    if hostport.startswith("["):
        return netloc
    port = ""
    if ":" in hostport:
        port = ":" + hostport.rsplit(":", 1)[1]
    return f"{userinfo}{new_host}{port}"


def _split_trail(raw: str) -> tuple[str, str]:
    url = raw
    trail = ""
    while url and url[-1] in TRAILING:
        trail = url[-1] + trail
        url = url[:-1]
    # A closing paren that was part of the URL (wikipedia-style) stays if balanced.
    while trail.startswith(")") and url.count("(") >= url.count(")") + 1:
        url += ")"
        trail = trail[1:]
    return url, trail
