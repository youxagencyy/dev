"""Environment-backed thresholds for the v1 watchlist."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE lines. Existing environment variables win."""
    env_path = path or Path(".env")
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            os.environ.setdefault(key, value)


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} должно быть числом, получено {raw!r}") from exc


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} должно быть целым числом, получено {raw!r}") from exc


def _env_str(name: str, default: str = "") -> str:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip()


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    min_outcome_price: float = 0.90
    max_outcome_price: float = 0.97
    min_liquidity_usd: float = 10_000
    min_volume_24h_usd: float = 5_000
    max_spread: float = 0.03
    min_hours_to_resolution: float = 2
    max_days_to_resolution: float = 14
    dedupe_hours: float = 12
    price_move_realert: float = 0.03
    poll_interval_seconds: float = 300
    gamma_page_limit: int = 100
    gamma_max_markets: int = 500
    max_clob_lookups: int = 40
    state_path: Path = Path(".alert-state.json")
    gamma_base: str = "https://gamma-api.polymarket.com"
    clob_base: str = "https://clob.polymarket.com"

    @classmethod
    def from_env(cls) -> Settings:
        settings = cls(
            telegram_bot_token=_env_str("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=_env_str("TELEGRAM_CHAT_ID"),
            min_outcome_price=_env_float("MIN_OUTCOME_PRICE", 0.90),
            max_outcome_price=_env_float("MAX_OUTCOME_PRICE", 0.97),
            min_liquidity_usd=_env_float("MIN_LIQUIDITY_USD", 10_000),
            min_volume_24h_usd=_env_float("MIN_VOLUME_24H_USD", 5_000),
            max_spread=_env_float("MAX_SPREAD", 0.03),
            min_hours_to_resolution=_env_float("MIN_HOURS_TO_RESOLUTION", 2),
            max_days_to_resolution=_env_float("MAX_DAYS_TO_RESOLUTION", 14),
            dedupe_hours=_env_float("DEDUPE_HOURS", 12),
            price_move_realert=_env_float("PRICE_MOVE_REALERT", 0.03),
            poll_interval_seconds=_env_float("POLL_INTERVAL_SECONDS", 300),
            gamma_page_limit=_env_int("GAMMA_PAGE_LIMIT", 100),
            gamma_max_markets=_env_int("GAMMA_MAX_MARKETS", 500),
            max_clob_lookups=_env_int("MAX_CLOB_LOOKUPS", 40),
            state_path=Path(_env_str("STATE_PATH", ".alert-state.json")),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.min_outcome_price >= self.max_outcome_price:
            raise SystemExit("MIN_OUTCOME_PRICE должен быть меньше MAX_OUTCOME_PRICE")
        if self.min_outcome_price <= 0 or self.max_outcome_price >= 1:
            raise SystemExit("ценовой диапазон должен лежать строго между 0 и 1")
        if self.max_spread <= 0:
            raise SystemExit("MAX_SPREAD должен быть больше 0")
        if self.min_liquidity_usd < 0 or self.min_volume_24h_usd < 0:
            raise SystemExit("ликвидность и объём не могут быть отрицательными")
        if self.min_hours_to_resolution < 0 or self.max_days_to_resolution <= 0:
            raise SystemExit("окно до резолва задано неверно")
        if self.min_hours_to_resolution >= self.max_days_to_resolution * 24:
            raise SystemExit("MIN_HOURS_TO_RESOLUTION длиннее MAX_DAYS_TO_RESOLUTION")
        if self.dedupe_hours < 0 or self.price_move_realert < 0:
            raise SystemExit("параметры дедупа не могут быть отрицательными")
        if self.poll_interval_seconds <= 0:
            raise SystemExit("POLL_INTERVAL_SECONDS должен быть больше 0")
        if self.gamma_page_limit <= 0 or self.gamma_max_markets <= 0:
            raise SystemExit("лимиты Gamma должны быть больше 0")
        if self.max_clob_lookups <= 0:
            raise SystemExit("MAX_CLOB_LOOKUPS должен быть больше 0")
