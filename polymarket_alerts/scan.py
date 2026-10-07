"""Turn Gamma markets and CLOB books into watchlist alerts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import quote

from polymarket_alerts.clob import BookTop, top_of_book
from polymarket_alerts.config import Settings
from polymarket_alerts.http_client import HttpError

FetchBook = Callable[[str], object]


@dataclass(frozen=True)
class Candidate:
    condition_id: str
    token_id: str
    question: str
    outcome: str
    gamma_price: float
    liquidity: float
    volume_24h: float
    end_date: datetime
    url: str


@dataclass(frozen=True)
class Alert:
    condition_id: str
    token_id: str
    question: str
    outcome: str
    ask: float
    bid: float
    spread: float
    liquidity: float
    volume_24h: float
    end_date: datetime
    hours_left: float
    url: str


def select_alerts(
    markets: list[dict],
    settings: Settings,
    fetch_book: FetchBook,
    now: datetime | None = None,
) -> list[Alert]:
    """Prefilter on Gamma, then confirm ask and spread on the outcome book."""
    moment = now or datetime.now(timezone.utc)
    candidates = _candidates(markets, settings, moment)
    candidates.sort(key=lambda item: item.volume_24h, reverse=True)
    alerts: list[Alert] = []
    lookups = 0
    seen_tokens: set[str] = set()
    for candidate in candidates:
        if candidate.token_id in seen_tokens:
            continue
        if lookups >= settings.max_clob_lookups:
            break
        seen_tokens.add(candidate.token_id)
        lookups += 1
        try:
            book = fetch_book(candidate.token_id)
        except HttpError:
            continue
        top = top_of_book(book)
        alert = _confirm(candidate, top, settings, moment)
        if alert is not None:
            alerts.append(alert)
    return alerts


def _candidates(markets: list[dict], settings: Settings, now: datetime) -> list[Candidate]:
    found: list[Candidate] = []
    seen: set[tuple[str, str]] = set()
    for market in markets:
        for candidate in _market_candidates(market, settings, now):
            key = (candidate.condition_id, candidate.token_id)
            if key in seen:
                continue
            seen.add(key)
            found.append(candidate)
    return found


def _market_candidates(market: dict, settings: Settings, now: datetime) -> list[Candidate]:
    if market.get("active") is not True or market.get("closed") is True:
        return []
    if market.get("acceptingOrders") is not True:
        return []
    if market.get("enableOrderBook") is False:
        return []
    end_date = _parse_time(market.get("endDate"))
    if end_date is None:
        return []
    hours_left = (end_date - now).total_seconds() / 3600
    max_hours = settings.max_days_to_resolution * 24
    if hours_left < settings.min_hours_to_resolution or hours_left > max_hours:
        return []
    liquidity = _first_float(market.get("liquidityNum"), market.get("liquidityClob"), market.get("liquidity"))
    volume = _first_float(market.get("volume24hr"), market.get("volume24hrClob"))
    if liquidity is None or volume is None:
        return []
    if liquidity < settings.min_liquidity_usd or volume < settings.min_volume_24h_usd:
        return []
    slug = _event_slug(market)
    condition_id = str(market.get("conditionId") or market.get("id") or "")
    question = str(market.get("question") or "").strip()
    if not slug or not condition_id or not question:
        return []
    try:
        outcomes = _json_list(market.get("outcomes"))
        prices = _json_list(market.get("outcomePrices"))
        token_ids = _json_list(market.get("clobTokenIds"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not (len(outcomes) == len(prices) == len(token_ids)) or not outcomes:
        return []
    url = "https://polymarket.com/event/" + quote(slug, safe="-_")
    picked: list[Candidate] = []
    for outcome, raw_price, token_id in zip(outcomes, prices, token_ids):
        try:
            price = float(raw_price)
        except (TypeError, ValueError):
            continue
        token = str(token_id or "").strip()
        label = str(outcome or "").strip()
        if not token or not label:
            continue
        if price < settings.min_outcome_price or price > settings.max_outcome_price:
            continue
        picked.append(
            Candidate(
                condition_id=condition_id,
                token_id=token,
                question=question,
                outcome=label,
                gamma_price=price,
                liquidity=liquidity,
                volume_24h=volume,
                end_date=end_date,
                url=url,
            )
        )
    return picked


def _confirm(candidate: Candidate, top: BookTop | None, settings: Settings, now: datetime) -> Alert | None:
    if top is None:
        return None
    if top.ask < settings.min_outcome_price or top.ask > settings.max_outcome_price:
        return None
    if top.spread > settings.max_spread:
        return None
    hours_left = (candidate.end_date - now).total_seconds() / 3600
    return Alert(
        condition_id=candidate.condition_id,
        token_id=candidate.token_id,
        question=candidate.question,
        outcome=candidate.outcome,
        ask=top.ask,
        bid=top.bid,
        spread=top.spread,
        liquidity=candidate.liquidity,
        volume_24h=candidate.volume_24h,
        end_date=candidate.end_date,
        hours_left=hours_left,
        url=candidate.url,
    )


def _event_slug(market: dict) -> str:
    events = market.get("events") or []
    if isinstance(events, list):
        for event in events:
            if isinstance(event, dict) and event.get("slug"):
                return str(event["slug"])
    if market.get("slug"):
        return str(market["slug"])
    return ""


def _json_list(value: object) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return parsed
    raise ValueError("expected a list")


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _first_float(*values: object) -> float | None:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None
