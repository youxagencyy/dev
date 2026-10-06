from __future__ import annotations

import asyncio
import time


class RateLimiter:
    """Minimum gap between posts and a rolling hourly cap. One publisher worker."""

    def __init__(self, min_interval_seconds: float, max_posts_per_hour: int) -> None:
        self.min_interval = min_interval_seconds
        self.max_per_hour = max_posts_per_hour
        self._last = 0.0
        self._stamps: list[float] = []
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                self._stamps = [stamp for stamp in self._stamps if stamp >= now - 3600]
                delay = 0.0
                if len(self._stamps) >= self.max_per_hour:
                    delay = self._stamps[0] + 3600 - now
                if self._last:
                    delay = max(delay, self.min_interval - (now - self._last))
                if delay <= 0:
                    self._last = now
                    self._stamps.append(now)
                    return
            await asyncio.sleep(delay)
