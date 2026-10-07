import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from polymarket_alerts.config import Settings, load_dotenv


class ConfigTests(unittest.TestCase):
    def test_defaults_match_the_v1_plan(self):
        settings = Settings()
        self.assertEqual(settings.min_outcome_price, 0.90)
        self.assertEqual(settings.max_outcome_price, 0.97)
        self.assertEqual(settings.min_liquidity_usd, 10_000)
        self.assertEqual(settings.min_volume_24h_usd, 5_000)
        self.assertEqual(settings.max_spread, 0.03)
        self.assertEqual(settings.min_hours_to_resolution, 2)
        self.assertEqual(settings.max_days_to_resolution, 14)
        self.assertEqual(settings.dedupe_hours, 12)
        self.assertEqual(settings.price_move_realert, 0.03)
        self.assertEqual(settings.poll_interval_seconds, 300)
        self.assertEqual(settings.gamma_max_markets, 500)
        self.assertEqual(settings.max_clob_lookups, 40)

    def test_dotenv_does_not_override_existing_env(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("MIN_OUTCOME_PRICE=0.5\nONLY_FROM_FILE=1\n", encoding="utf-8")
            previous = os.environ.get("MIN_OUTCOME_PRICE")
            os.environ["MIN_OUTCOME_PRICE"] = "0.91"
            try:
                load_dotenv(path)
                self.assertEqual(os.environ["MIN_OUTCOME_PRICE"], "0.91")
                self.assertEqual(os.environ["ONLY_FROM_FILE"], "1")
            finally:
                os.environ.pop("ONLY_FROM_FILE", None)
                if previous is None:
                    os.environ.pop("MIN_OUTCOME_PRICE", None)
                else:
                    os.environ["MIN_OUTCOME_PRICE"] = previous

    def test_inverted_price_band_is_rejected(self):
        previous_min = os.environ.get("MIN_OUTCOME_PRICE")
        previous_max = os.environ.get("MAX_OUTCOME_PRICE")
        os.environ["MIN_OUTCOME_PRICE"] = "0.99"
        os.environ["MAX_OUTCOME_PRICE"] = "0.90"
        try:
            with self.assertRaises(SystemExit):
                Settings.from_env()
        finally:
            if previous_min is None:
                os.environ.pop("MIN_OUTCOME_PRICE", None)
            else:
                os.environ["MIN_OUTCOME_PRICE"] = previous_min
            if previous_max is None:
                os.environ.pop("MAX_OUTCOME_PRICE", None)
            else:
                os.environ["MAX_OUTCOME_PRICE"] = previous_max


if __name__ == "__main__":
    unittest.main()
