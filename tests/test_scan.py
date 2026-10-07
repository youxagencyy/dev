import unittest
from datetime import datetime, timezone

from polymarket_alerts.clob import top_of_book
from polymarket_alerts.config import Settings
from polymarket_alerts.scan import market_url, select_alerts

NOW = datetime(2026, 10, 7, 22, 0, tzinfo=timezone.utc)


def market(**overrides):
    base = {
        "id": "1",
        "conditionId": "0xabc",
        "question": "Will it rain on Friday?",
        "slug": "will-it-rain",
        "events": [{"slug": "will-it-rain-event"}],
        "outcomes": '["Yes", "No"]',
        "outcomePrices": '["0.93", "0.07"]',
        "clobTokenIds": '["yes-token", "no-token"]',
        "liquidityNum": 20000,
        "volume24hr": 8000,
        "endDate": "2026-10-10T22:00:00Z",
        "active": True,
        "closed": False,
        "acceptingOrders": True,
        "enableOrderBook": True,
    }
    base.update(overrides)
    return base


def tight_book():
    # Worst prices are listed first, the way the live CLOB sometimes returns them.
    return {
        "bids": [{"price": "0.01", "size": "100"}, {"price": "0.910", "size": "20"}],
        "asks": [{"price": "0.99", "size": "100"}, {"price": "0.930", "size": "15"}],
    }


class MarketUrlTests(unittest.TestCase):
    def test_event_and_market_slugs_both_appear_when_they_differ(self):
        url = market_url(market())
        self.assertEqual(url, "https://polymarket.com/event/will-it-rain-event/will-it-rain")

    def test_matching_slugs_stay_on_the_event_page(self):
        url = market_url(market(slug="will-it-rain-event"))
        self.assertEqual(url, "https://polymarket.com/event/will-it-rain-event")


class TopOfBookTests(unittest.TestCase):
    def test_uses_best_prices_not_first_row(self):
        top = top_of_book(tight_book())
        self.assertEqual((top.bid, top.ask), (0.91, 0.93))

    def test_empty_side_is_unusable(self):
        self.assertIsNone(top_of_book({"bids": [], "asks": [{"price": "0.93"}]}))

    def test_crossed_book_is_unusable(self):
        book = {"bids": [{"price": "0.95"}], "asks": [{"price": "0.90"}]}
        self.assertIsNone(top_of_book(book))


class SelectAlertsTests(unittest.TestCase):
    def test_keeps_ask_inside_band_with_tight_spread(self):
        alerts = select_alerts([market()], Settings(), lambda _token: tight_book(), now=NOW)
        self.assertEqual(len(alerts), 1)
        alert = alerts[0]
        self.assertEqual(alert.outcome, "Yes")
        self.assertEqual(alert.ask, 0.93)
        self.assertAlmostEqual(alert.spread, 0.02)
        self.assertEqual(
            alert.url,
            "https://polymarket.com/event/will-it-rain-event/will-it-rain",
        )

    def test_rejects_price_above_ceiling_and_below_floor(self):
        high = market(id="2", outcomePrices='["0.999", "0.001"]')
        low = market(id="3", conditionId="0xlow", outcomePrices='["0.80", "0.20"]')
        alerts = select_alerts([high, low], Settings(), lambda _token: tight_book(), now=NOW)
        self.assertEqual(alerts, [])

    def test_rejects_wide_clob_spread_even_if_gamma_price_matches(self):
        wide = {
            "bids": [{"price": "0.80", "size": "10"}],
            "asks": [{"price": "0.93", "size": "10"}],
        }
        alerts = select_alerts([market()], Settings(), lambda _token: wide, now=NOW)
        self.assertEqual(alerts, [])

    def test_rejects_when_ask_leaves_the_band(self):
        moved = {
            "bids": [{"price": "0.97", "size": "10"}],
            "asks": [{"price": "0.985", "size": "10"}],
        }
        alerts = select_alerts([market()], Settings(), lambda _token: moved, now=NOW)
        self.assertEqual(alerts, [])

    def test_rejects_low_liquidity_far_end_and_closed(self):
        samples = [
            market(liquidityNum=100),
            market(volume24hr=10),
            market(endDate="2027-01-01T00:00:00Z"),
            market(endDate="2026-10-07T23:00:00Z"),
            market(closed=True),
            market(acceptingOrders=False),
            market(active=False),
        ]
        alerts = select_alerts(samples, Settings(), lambda _token: tight_book(), now=NOW)
        self.assertEqual(alerts, [])

    def test_stops_at_clob_lookup_cap_and_prefers_higher_volume(self):
        settings = Settings(max_clob_lookups=1)
        quiet = market(id="q", conditionId="0xq", volume24hr=6000, clobTokenIds='["quiet", "no-q"]')
        busy = market(id="b", conditionId="0xb", volume24hr=90000, clobTokenIds='["busy", "no-b"]')
        seen = []

        def fetch(token_id):
            seen.append(token_id)
            return tight_book()

        alerts = select_alerts([quiet, busy], settings, fetch, now=NOW)
        self.assertEqual(seen, ["busy"])
        self.assertEqual(alerts[0].token_id, "busy")

    def test_skips_a_book_that_fails_to_load(self):
        from polymarket_alerts.http_client import HttpError

        def fetch(_token):
            raise HttpError("временный сбой")

        alerts = select_alerts([market()], Settings(), fetch, now=NOW)
        self.assertEqual(alerts, [])


if __name__ == "__main__":
    unittest.main()
