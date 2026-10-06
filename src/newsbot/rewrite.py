from __future__ import annotations

import re
from typing import Protocol

import httpx

from newsbot.config import RewriteConfig

FENCE_RE = re.compile(r"^```[a-zA-Z0-9]*\n([\s\S]*?)\n```$")


class RewriteClient(Protocol):
    active: bool

    async def rewrite(self, text: str) -> tuple[str, str | None]:
        """Return (text, error). Error is None when rewrite ran or was skipped."""


class Rewriter:
    """OpenAI-compatible chat completions.

    When the API key is missing or ``rewrite.enabled`` is false, ``active``
    is false and ``rewrite`` returns the original text. Callers still clean
    and publish. Failures also return the original text plus a short error
    that does not include the key.
    """

    def __init__(
        self,
        config: RewriteConfig,
        *,
        api_key: str,
        base_url: str,
        model: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = client

    @property
    def active(self) -> bool:
        return self.config.enabled and bool(self.api_key)

    async def rewrite(self, text: str) -> tuple[str, str | None]:
        if not self.active:
            return text, None
        payload = {
            "model": self.model,
            "temperature": self.config.temperature,
            "messages": [
                {"role": "system", "content": self.config.system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Тон: {self.config.tone}\n"
                        f"Максимум символов: {self.config.max_length}\n"
                        "Перепиши новость. Верни только готовый текст.\n\n"
                        f"{text}"
                    ),
                },
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}/chat/completions"
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            return text, f"HTTP {exc.response.status_code}"
        except httpx.HTTPError as exc:
            return text, exc.__class__.__name__
        except ValueError:
            return text, "bad_response"
        finally:
            if owns_client:
                await client.aclose()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return text, "bad_response"
        cleaned = _unwrap(str(content or ""))
        if not cleaned:
            return text, "empty_response"
        if len(cleaned) > self.config.max_length:
            cleaned = cleaned[: self.config.max_length].rstrip()
        return cleaned, None


def _unwrap(content: str) -> str:
    text = content.strip()
    fenced = FENCE_RE.match(text)
    if fenced:
        return fenced.group(1).strip()
    return text
