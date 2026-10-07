"""Russian Telegram text for one watchlist alert."""

from __future__ import annotations

from polymarket_alerts.config import Settings
from polymarket_alerts.scan import Alert


def format_alert(alert: Alert, settings: Settings) -> str:
    ask_pct = alert.ask * 100
    when = alert.end_date.strftime("%Y-%m-%d %H:%M UTC")
    reason = (
        f"ask {_price(alert.ask)} в диапазоне {_num(settings.min_outcome_price)}–{_num(settings.max_outcome_price)}; "
        f"спред {_price(alert.spread)} ≤ {_num(settings.max_spread)}; "
        f"ликвидность {_usd(alert.liquidity)} ≥ {_usd(settings.min_liquidity_usd)}; "
        f"объём 24ч {_usd(alert.volume_24h)} ≥ {_usd(settings.min_volume_24h_usd)}; "
        f"до резолва {alert.hours_left:.0f} ч "
        f"(окно {_num(settings.min_hours_to_resolution)} ч – {_num(settings.max_days_to_resolution)} д)"
    )
    lines = [
        "Polymarket",
        "",
        f"Рынок: {alert.question}",
        f"Исход: {alert.outcome}",
        f"Цена покупки (ask): {_price(alert.ask)} ({ask_pct:.1f}%)",
        f"Лучший bid: {_price(alert.bid)}",
        f"Спред: {_price(alert.spread)}",
        f"Ликвидность: {_usd(alert.liquidity)}",
        f"Объём 24ч: {_usd(alert.volume_24h)}",
        f"До конца: {_horizon(alert.hours_left)}",
        f"Резолв (endDate): {when}",
        f"Ссылка: {alert.url}",
        "",
        f"Почему сработало: {reason}.",
        "",
        "Цена — уже вероятность рынка. Выплата тонкая, хвост остаётся. Это список наблюдения, не преимущество.",
    ]
    return "\n".join(lines)


def _price(value: float) -> str:
    return f"{value:.3f}"


def _num(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    if "." not in text:
        return text
    whole, fraction = text.split(".", 1)
    if len(fraction) < 2:
        fraction = fraction.ljust(2, "0")
    return f"{whole}.{fraction}"


def _usd(value: float) -> str:
    return f"${value:,.0f}"


def _horizon(hours: float) -> str:
    total_minutes = max(0, int(round(hours * 60)))
    days, rem = divmod(total_minutes, 60 * 24)
    hrs, minutes = divmod(rem, 60)
    if days:
        return f"{days} д {hrs} ч"
    if hrs:
        return f"{hrs} ч {minutes} мин"
    return f"{minutes} мин"
