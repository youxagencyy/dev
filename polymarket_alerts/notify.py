"""Delivery interface. Dry-run prints; Telegram is used only with both credentials."""

from __future__ import annotations

import sys
from typing import Callable, Protocol, TextIO

from polymarket_alerts.http_client import post_json


class Notifier(Protocol):
    def send(self, text: str) -> None:
        """Deliver one alert body."""


class DryRunNotifier:
    def __init__(self, out: TextIO | None = None) -> None:
        self._out = out if out is not None else sys.stdout

    def send(self, text: str) -> None:
        print(text, file=self._out)
        print(file=self._out)


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, post: Callable[..., object] | None = None) -> None:
        self._token = token
        self._chat_id = chat_id
        self._post = post or post_json

    def send(self, text: str) -> None:
        body = text if len(text) <= 4000 else text[:4000]
        self._post(
            f"https://api.telegram.org/bot{self._token}/sendMessage",
            {
                "chat_id": self._chat_id,
                "text": body,
                "disable_web_page_preview": True,
            },
        )


def build_notifier(
    token: str,
    chat_id: str,
    *,
    out: TextIO | None = None,
    post: Callable[..., object] | None = None,
) -> tuple[Notifier, str]:
    if token.strip() and chat_id.strip():
        return TelegramNotifier(token.strip(), chat_id.strip(), post=post), "telegram"
    return DryRunNotifier(out=out), "dry-run"
