import unittest
from datetime import datetime, timezone

from polymarket_alerts.config import Settings
from polymarket_alerts.messages import format_alert
from polymarket_alerts.scan import Alert


class MessageTests(unittest.TestCase):
    def test_message_has_market_outcome_price_link_and_reason(self):
        alert = Alert(
            condition_id="0xabc",
            token_id="yes-token",
            question="Will it rain on Friday?",
            outcome="Yes",
            ask=0.93,
            bid=0.91,
            spread=0.02,
            liquidity=20000,
            volume_24h=8000,
            end_date=datetime(2026, 10, 10, 22, 0, tzinfo=timezone.utc),
            hours_left=72,
            url="https://polymarket.com/event/will-it-rain-event",
        )
        text = format_alert(alert, Settings())
        self.assertIn("Рынок: Will it rain on Friday?", text)
        self.assertIn("Исход: Yes", text)
        self.assertIn("Цена покупки (ask): 0.930 (93.0%)", text)
        self.assertIn("Ссылка: https://polymarket.com/event/will-it-rain-event", text)
        self.assertIn("Почему сработало:", text)
        self.assertIn("0.90–0.97", text)
        self.assertIn("спред 0.020 ≤ 0.03", text)
        self.assertIn("не преимущество", text)


if __name__ == "__main__":
    unittest.main()
