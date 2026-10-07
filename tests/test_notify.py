import io
import unittest

from polymarket_alerts.notify import build_notifier


class NotifyTests(unittest.TestCase):
    def test_missing_token_is_dry_run(self):
        sent = []
        output = io.StringIO()

        def post(url, payload):
            sent.append((url, payload))

        notifier, mode = build_notifier("", "123", out=output, post=post)
        notifier.send("привет")
        self.assertIn("привет", output.getvalue())
        self.assertEqual(mode, "dry-run")
        self.assertEqual(sent, [])

    def test_token_and_chat_call_telegram(self):
        sent = []

        def post(url, payload):
            sent.append((url, payload))

        notifier, mode = build_notifier("token-value", "123", post=post)
        notifier.send("привет")
        self.assertEqual(mode, "telegram")
        self.assertEqual(len(sent), 1)
        self.assertTrue(sent[0][0].endswith("/sendMessage"))
        self.assertEqual(sent[0][1]["chat_id"], "123")
        self.assertEqual(sent[0][1]["text"], "привет")
        self.assertNotIn("token-value", sent[0][1]["text"])


if __name__ == "__main__":
    unittest.main()
