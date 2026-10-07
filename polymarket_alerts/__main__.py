"""CLI: python -m polymarket_alerts [--loop]."""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

from polymarket_alerts.app import run_once
from polymarket_alerts.config import Settings, load_dotenv
from polymarket_alerts.http_client import HttpError, get_json
from polymarket_alerts.notify import build_notifier


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = _parse_args(argv)
    settings = Settings.from_env()
    if args.state:
        settings = replace(settings, state_path=Path(args.state))
    notifier, mode = build_notifier(settings.telegram_bot_token, settings.telegram_chat_id)
    if mode == "dry-run":
        print(
            "TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID пуст — dry-run, сообщения печатаются в консоль.",
            file=sys.stderr,
        )
    while True:
        try:
            sent, scanned, matched = run_once(settings, notifier, get_json)
            print(
                f"обход: рынков {scanned}, прошли фильтр {matched}, отправлено {sent}, режим {mode}",
                file=sys.stderr,
            )
        except (HttpError, OSError, ValueError) as exc:
            print(f"ошибка обхода: {exc}", file=sys.stderr)
            if not args.loop:
                return 1
        if not args.loop:
            return 0
        time.sleep(settings.poll_interval_seconds)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Список наблюдения Polymarket: высокая цена ask, без ордеров и без кошелька."
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="повторять обход каждые POLL_INTERVAL_SECONDS",
    )
    parser.add_argument("--state", help="путь к файлу дедупа вместо STATE_PATH")
    return parser.parse_args(argv)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(0) from None
