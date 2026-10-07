import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from polymarket_alerts.dedupe import DedupeStore


NOW = datetime(2026, 10, 7, 22, 0, tzinfo=timezone.utc)


class DedupeTests(unittest.TestCase):
    def test_repeat_is_suppressed_until_time_or_price_moves(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            store = DedupeStore(path)
            store.load()
            self.assertTrue(store.should_send("m|t", 0.93, NOW, dedupe_hours=12, price_move=0.03))
            store.mark("m|t", 0.93, NOW)
            store.save()

            again = DedupeStore(path)
            again.load()
            later = NOW + timedelta(hours=1)
            self.assertFalse(again.should_send("m|t", 0.94, later, dedupe_hours=12, price_move=0.03))
            self.assertTrue(again.should_send("m|t", 0.96, later, dedupe_hours=12, price_move=0.03))
            self.assertTrue(
                again.should_send(
                    "m|t",
                    0.93,
                    NOW + timedelta(hours=12),
                    dedupe_hours=12,
                    price_move=0.03,
                )
            )

    def test_corrupt_state_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text("[]", encoding="utf-8")
            store = DedupeStore(path)
            with self.assertRaises(ValueError):
                store.load()


if __name__ == "__main__":
    unittest.main()
