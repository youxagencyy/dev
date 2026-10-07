"""Remember which outcome alerts were already delivered."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class DedupeStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._rows: dict[str, dict[str, str | float]] = {}

    def load(self) -> None:
        if not self.path.is_file():
            self._rows = {}
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"{self.path} повреждён: ожидался объект JSON")
        alerts = raw.get("alerts", {})
        if not isinstance(alerts, dict):
            raise ValueError(f"{self.path} повреждён: поле alerts")
        self._rows = alerts

    def should_send(
        self,
        key: str,
        price: float,
        now: datetime,
        *,
        dedupe_hours: float,
        price_move: float,
    ) -> bool:
        row = self._rows.get(key)
        if not row:
            return True
        previous = float(row["price"])
        sent_at = datetime.fromisoformat(str(row["at"]))
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        age_hours = (now - sent_at).total_seconds() / 3600
        if age_hours >= dedupe_hours:
            return True
        # Prices are quoted to 0.001; round so 0.96 - 0.93 counts as a 0.03 move.
        return round(abs(price - previous), 4) >= price_move

    def mark(self, key: str, price: float, now: datetime) -> None:
        self._rows[key] = {"price": price, "at": now.astimezone(timezone.utc).isoformat()}

    def save(self) -> None:
        if self.path.parent and str(self.path.parent) not in {"", "."}:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"alerts": self._rows}, ensure_ascii=False, indent=2)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(payload + "\n", encoding="utf-8")
        temporary.replace(self.path)


def alert_key(condition_id: str, token_id: str) -> str:
    return f"{condition_id}|{token_id}"
