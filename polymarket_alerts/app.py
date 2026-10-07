"""One scan: fetch, filter, dedupe, deliver."""

from __future__ import annotations

from datetime import datetime, timezone

from polymarket_alerts.clob import fetch_book
from polymarket_alerts.config import Settings
from polymarket_alerts.dedupe import DedupeStore, alert_key
from polymarket_alerts.gamma import fetch_active_markets
from polymarket_alerts.messages import format_alert
from polymarket_alerts.notify import Notifier
from polymarket_alerts.scan import select_alerts


def run_once(
    settings: Settings,
    notifier: Notifier,
    get_json,
    now: datetime | None = None,
) -> tuple[int, int, int]:
    """Return (sent, markets_scanned, alerts_matched)."""
    moment = now or datetime.now(timezone.utc)
    markets = fetch_active_markets(get_json, settings)

    def load_book(token_id: str):
        return fetch_book(get_json, settings, token_id)

    alerts = select_alerts(markets, settings, load_book, now=moment)
    store = DedupeStore(settings.state_path)
    store.load()
    sent = 0
    for alert in alerts:
        key = alert_key(alert.condition_id, alert.token_id)
        if not store.should_send(
            key,
            alert.ask,
            moment,
            dedupe_hours=settings.dedupe_hours,
            price_move=settings.price_move_realert,
        ):
            continue
        notifier.send(format_alert(alert, settings))
        store.mark(key, alert.ask, moment)
        store.save()
        sent += 1
    return sent, len(markets), len(alerts)
