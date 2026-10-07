"""Read the public CLOB order book for one outcome token."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlencode

from polymarket_alerts.config import Settings

GetJson = Callable[[str], object]


@dataclass(frozen=True)
class BookTop:
    bid: float
    ask: float

    @property
    def spread(self) -> float:
        return self.ask - self.bid


def fetch_book(get_json: GetJson, settings: Settings, token_id: str) -> object:
    query = urlencode({"token_id": token_id})
    return get_json(f"{settings.clob_base}/book?{query}")


def top_of_book(book: object) -> BookTop | None:
    """Best bid is the highest bid, best ask is the lowest ask.

    The public book is not guaranteed to arrive best-price first.
    """
    if not isinstance(book, dict):
        return None
    bid_prices = _prices(book.get("bids"))
    ask_prices = _prices(book.get("asks"))
    if not bid_prices or not ask_prices:
        return None
    bid = max(bid_prices)
    ask = min(ask_prices)
    if ask < bid:
        return None
    return BookTop(bid=bid, ask=ask)


def _prices(levels: object) -> list[float]:
    if not isinstance(levels, list):
        return []
    prices: list[float] = []
    for level in levels:
        if not isinstance(level, dict):
            continue
        raw = level.get("price")
        try:
            price = float(raw)
        except (TypeError, ValueError):
            continue
        prices.append(price)
    return prices
