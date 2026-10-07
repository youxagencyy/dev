import io
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from polymarket_alerts.app import run_once
from polymarket_alerts.config import Settings
from polymarket_alerts.gamma import fetch_active_markets
from polymarket_alerts.notify import DryRunNotifier

NOW = datetime(2026, 10, 7, 22, 0, tzinfo=timezone.utc)


def market(market_id="1"):
    return {
        "id": market_id,
        "conditionId": f"0x{market_id}",
        "question": "Will it rain on Friday?",
        "slug": "will-it-rain",
        "events": [{"slug": "will-it-rain-event"}],
        "outcomes": '["Yes", "No"]',
        "outcomePrices": '["0.93", "0.07"]',
        "clobTokenIds": [f"yes-{market_id}", f"no-{market_id}"],
        "liquidityNum": 20000,
        "volume24hr": 8000,
        "endDate": "2026-10-10T22:00:00Z",
        "active": True,
        "closed": False,
        "acceptingOrders": True,
        "enableOrderBook": True,
    }


class FakeHttp:
    def __init__(self):
        self.gamma_calls = 0

    def __call__(self, url):
        if "/markets?" in url:
            self.gamma_calls += 1
            if self.gamma_calls == 1:
                return [market("1"), market("1"), market("2")]
            return []
        if "/book?" in url:
            return {
                "bids": [{"price": "0.01"}, {"price": "0.91"}],
                "asks": [{"price": "0.99"}, {"price": "0.93"}],
            }
        raise AssertionError(url)


class AppTests(unittest.TestCase):
    def test_run_once_prints_and_dedupes(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(state_path=Path(directory) / "state.json", gamma_max_markets=10)
            output = io.StringIO()
            http = FakeHttp()
            sent, scanned, matched = run_once(settings, DryRunNotifier(output), http, now=NOW)
            self.assertEqual((sent, scanned, matched), (2, 2, 2))
            text = output.getvalue()
            self.assertIn("Исход: Yes", text)
            self.assertIn("https://polymarket.com/event/will-it-rain-event", text)

            output.seek(0)
            output.truncate(0)
            sent_again, _, _ = run_once(settings, DryRunNotifier(output), FakeHttp(), now=NOW)
            self.assertEqual(sent_again, 0)
            self.assertEqual(output.getvalue(), "")

    def test_gamma_pagination_stops_on_short_page(self):
        calls = []

        def get_json(url):
            calls.append(url)
            if "offset=0" in url:
                return [market("1")]
            return []

        settings = Settings(gamma_page_limit=2, gamma_max_markets=10)
        markets = fetch_active_markets(get_json, settings)
        self.assertEqual(len(markets), 1)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
