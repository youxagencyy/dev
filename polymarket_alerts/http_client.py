"""Small JSON client for public Polymarket reads and Telegram delivery."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Callable

USER_AGENT = "polymarket-alert-bot/0.1"


class HttpError(Exception):
    """A public request failed. The message must not include bot tokens."""


def get_json(url: str, timeout: float = 20.0, sleeper: Callable[[float], None] = time.sleep) -> object:
    return _request(url, timeout=timeout, data=None, method="GET", sleeper=sleeper, secret=False)


def post_json(
    url: str,
    payload: dict,
    timeout: float = 20.0,
    sleeper: Callable[[float], None] = time.sleep,
) -> object:
    data = json.dumps(payload).encode("utf-8")
    body = _request(url, timeout=timeout, data=data, method="POST", sleeper=sleeper, secret=True)
    if isinstance(body, dict) and body.get("ok") is False:
        description = body.get("description") or "Telegram отклонил сообщение"
        raise HttpError(str(description))
    return body


def _request(
    url: str,
    *,
    timeout: float,
    data: bytes | None,
    method: str,
    sleeper: Callable[[float], None],
    secret: bool,
) -> object:
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if attempt == 0 and exc.code in {429, 500, 502, 503, 504}:
                sleeper(1.0)
                continue
            target = "Telegram" if secret else url
            raise HttpError(f"HTTP {exc.code} для {target}") from exc
        except urllib.error.URLError as exc:
            last_error = exc
            if attempt == 0:
                sleeper(1.0)
                continue
            reason = getattr(exc, "reason", exc)
            target = "Telegram" if secret else url
            raise HttpError(f"сеть недоступна для {target}: {reason}") from exc
        except json.JSONDecodeError as exc:
            target = "Telegram" if secret else url
            raise HttpError(f"ответ не JSON: {target}") from exc
    raise HttpError("запрос не удался")
