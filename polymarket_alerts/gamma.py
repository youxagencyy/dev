"""Fetch active markets from the public Gamma API."""

from __future__ import annotations

from typing import Callable
from urllib.parse import urlencode

from polymarket_alerts.config import Settings
from polymarket_alerts.http_client import HttpError

GetJson = Callable[[str], object]


def fetch_active_markets(get_json: GetJson, settings: Settings) -> list[dict]:
    """Page markets ordered by 24h volume. Duplicate ids across pages are skipped."""
    markets: list[dict] = []
    seen: set[str] = set()
    offset = 0
    while len(markets) < settings.gamma_max_markets:
        take = min(settings.gamma_page_limit, settings.gamma_max_markets - len(markets))
        query = urlencode(
            {
                "active": "true",
                "closed": "false",
                "limit": take,
                "offset": offset,
                "order": "volume24hr",
                "ascending": "false",
            }
        )
        url = f"{settings.gamma_base}/markets?{query}"
        page = get_json(url)
        if not isinstance(page, list):
            raise HttpError("Gamma вернул не список рынков")
        if not page:
            break
        added = 0
        for item in page:
            if not isinstance(item, dict):
                continue
            market_id = str(item.get("id") or "")
            if market_id and market_id in seen:
                continue
            if market_id:
                seen.add(market_id)
            markets.append(item)
            added += 1
            if len(markets) >= settings.gamma_max_markets:
                break
        if added == 0 or len(page) < take:
            break
        offset += len(page)
    return markets
