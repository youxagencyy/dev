from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from newsbot.textutil import fold

USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")


@dataclass(frozen=True)
class Donor:
    username: str
    enabled: bool = True
    signature: str | None = None


@dataclass(frozen=True)
class SignatureConfig:
    default: str
    templates: dict[str, str]
    channel_link: str
    hashtags: str
    channel_title: str


@dataclass(frozen=True)
class AdFilterConfig:
    """Documented heuristic, applied in this order:

    1. Casefolded substring hits against ``keywords``. A post is an ad when
       the number of distinct hits is >= ``min_hits``.
    2. A post is an ad when the number of http(s) URLs is > ``max_external_links``.
    3. A post is an ad when any expression in ``patterns`` matches.

    There is no hidden score. A news sentence that quotes a blocked phrase
    is dropped; raise ``min_hits`` or edit the list.
    """

    keywords: tuple[str, ...]
    min_hits: int
    max_external_links: int
    patterns: tuple[re.Pattern[str], ...]


@dataclass(frozen=True)
class StripConfig:
    patterns: tuple[re.Pattern[str], ...]
    trailing_markers: tuple[str, ...]


@dataclass(frozen=True)
class LinkConfig:
    strip_params: frozenset[str]
    domain_rewrite: dict[str, str]
    blacklist_domains: frozenset[str]


@dataclass(frozen=True)
class RewriteConfig:
    enabled: bool
    tone: str
    max_length: int
    keep_media_captions: bool
    system_prompt: str
    temperature: float


@dataclass(frozen=True)
class DedupeConfig:
    window_hours: float
    similarity_threshold: float
    min_tokens: int


@dataclass(frozen=True)
class RateLimitConfig:
    min_interval_seconds: float
    max_posts_per_hour: int


@dataclass(frozen=True)
class PublishConfig:
    album_flush_seconds: float
    album_max_items: int
    caption_limit: int
    message_limit: int


@dataclass(frozen=True)
class Config:
    target_channel: str
    owner_id: int
    donors: tuple[Donor, ...]
    signatures: SignatureConfig
    ad_filter: AdFilterConfig
    strip: StripConfig
    links: LinkConfig
    rewrite: RewriteConfig
    dedupe: DedupeConfig
    rate_limit: RateLimitConfig
    publish: PublishConfig


@dataclass(frozen=True)
class Settings:
    api_id: int
    api_hash: str
    session: str
    bot_token: str
    openai_base_url: str
    openai_model: str
    openai_api_key: str
    database_path: str
    config_path: str


class ConfigError(SystemExit):
    """Invalid config or environment. ``SystemExit`` so the process stops cleanly."""


def load_config(path: str | Path | None = None) -> Config:
    raw_path = Path(path or os.environ.get("CONFIG_PATH", "config.yaml"))
    if not raw_path.is_file():
        raise ConfigError(
            f"Нет файла конфигурации {raw_path}. "
            "Скопируйте config.example.yaml в config.yaml и заполните его."
        )
    with raw_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ConfigError("Корень config.yaml должен быть словарём")
    return parse_config(data)


def parse_config(data: dict) -> Config:
    target = _mapping(data.get("target"), "target")
    channel = _text(target.get("channel"), "target.channel")
    owner_id = data.get("owner_id")
    if isinstance(owner_id, bool) or not isinstance(owner_id, int) or owner_id <= 0:
        raise ConfigError("owner_id должен быть положительным числом Telegram user id")

    signatures = _signatures(_mapping(data.get("signatures"), "signatures"))
    donors = _donors(data.get("donors"), signatures)
    ad_filter = _ad_filter(_mapping(data.get("ad_filter"), "ad_filter"))
    strip = _strip(_mapping(data.get("strip"), "strip"))
    links = _links(_mapping(data.get("links"), "links"))
    rewrite = _rewrite(_mapping(data.get("rewrite"), "rewrite"))
    dedupe = _dedupe(_mapping(data.get("dedupe"), "dedupe"))
    rate_limit = _rate_limit(_mapping(data.get("rate_limit"), "rate_limit"))
    publish = _publish(_mapping(data.get("publish") or {}, "publish"))
    return Config(
        target_channel=channel,
        owner_id=owner_id,
        donors=donors,
        signatures=signatures,
        ad_filter=ad_filter,
        strip=strip,
        links=links,
        rewrite=rewrite,
        dedupe=dedupe,
        rate_limit=rate_limit,
        publish=publish,
    )


def load_settings() -> Settings:
    api_id_raw = _env("TELEGRAM_API_ID")
    if not api_id_raw.isdigit():
        raise ConfigError("TELEGRAM_API_ID должен быть числом с https://my.telegram.org")
    return Settings(
        api_id=int(api_id_raw),
        api_hash=_env("TELEGRAM_API_HASH"),
        session=os.getenv("TELEGRAM_SESSION", "").strip(),
        bot_token=_env("BOT_TOKEN"),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
        or "https://api.openai.com/v1",
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        database_path=os.getenv("DATABASE_PATH", "data/newsbot.sqlite").strip()
        or "data/newsbot.sqlite",
        config_path=os.getenv("CONFIG_PATH", "config.yaml").strip() or "config.yaml",
    )


def chat_target(channel: str) -> str | int:
    text = channel.strip()
    if text.lstrip("-").isdigit():
        return int(text)
    return text


def _env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"Не задана переменная окружения {name}")
    return value


def _mapping(value: object, field: str) -> dict:
    if not isinstance(value, dict):
        raise ConfigError(f"{field} должен быть словарём")
    return value


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{field} должен быть непустой строкой")
    return value.strip()


def _optional_text(value: object, field: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ConfigError(f"{field} должен быть строкой")
    return value.strip()


def _int(value: object, field: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ConfigError(f"{field} должен быть целым числом >= {minimum}")
    return value


def _number(value: object, field: str, *, minimum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < minimum:
        raise ConfigError(f"{field} должен быть числом >= {minimum}")
    return float(value)


def _bool(value: object, field: str, default: bool = False) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ConfigError(f"{field} должен быть true или false")
    return value


def _str_tuple(value: object, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{field} должен быть списком строк")
    return tuple(item.strip() for item in value if item.strip())


def _compile_all(patterns: tuple[str, ...], field: str) -> tuple[re.Pattern[str], ...]:
    compiled: list[re.Pattern[str]] = []
    for pattern in patterns:
        try:
            compiled.append(re.compile(pattern))
        except re.error as exc:
            raise ConfigError(f"{field}: некорректное выражение {pattern!r}: {exc}") from exc
    return tuple(compiled)


def _signatures(data: dict) -> SignatureConfig:
    templates_raw = data.get("templates")
    if not isinstance(templates_raw, dict) or not templates_raw:
        raise ConfigError("signatures.templates должен быть непустым словарём")
    templates: dict[str, str] = {}
    for name, template in templates_raw.items():
        if not isinstance(name, str) or not isinstance(template, str) or not template.strip():
            raise ConfigError("signatures.templates: имена и тексты должны быть непустыми строками")
        templates[name.strip()] = template.strip()
    default = _text(data.get("default"), "signatures.default")
    if default not in templates:
        raise ConfigError(f"signatures.default={default!r} нет в signatures.templates")
    return SignatureConfig(
        default=default,
        templates=templates,
        channel_link=_optional_text(data.get("channel_link"), "signatures.channel_link"),
        hashtags=_optional_text(data.get("hashtags"), "signatures.hashtags"),
        channel_title=_optional_text(data.get("channel_title"), "signatures.channel_title"),
    )


def _donors(value: object, signatures: SignatureConfig) -> tuple[Donor, ...]:
    if not isinstance(value, list) or not value:
        raise ConfigError("donors должен быть непустым списком")
    donors: list[Donor] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        field = f"donors[{index}]"
        data = _mapping(item, field)
        username = _text(data.get("username"), f"{field}.username").lstrip("@")
        if not USERNAME_RE.match(username):
            raise ConfigError(
                f"{field}.username={username!r} не похож на публичный username канала"
            )
        key = username.casefold()
        if key in seen:
            raise ConfigError(f"Донор @{username} указан дважды")
        seen.add(key)
        signature = data.get("signature")
        template: str | None
        if signature is None or signature == "":
            template = None
        elif isinstance(signature, str):
            template = signature.strip()
            if template not in signatures.templates:
                raise ConfigError(f"{field}.signature={template!r} нет среди шаблонов подписи")
        else:
            raise ConfigError(f"{field}.signature должен быть строкой")
        donors.append(
            Donor(
                username=username,
                enabled=_bool(data.get("enabled"), f"{field}.enabled", default=True),
                signature=template,
            )
        )
    return tuple(donors)


def _ad_filter(data: dict) -> AdFilterConfig:
    keywords = tuple(fold_keyword(item) for item in _str_tuple(data.get("keywords"), "ad_filter.keywords"))
    keywords = tuple(item for item in keywords if item)
    return AdFilterConfig(
        keywords=keywords,
        min_hits=_int(data.get("min_hits", 1), "ad_filter.min_hits", minimum=1),
        max_external_links=_int(
            data.get("max_external_links", 5),
            "ad_filter.max_external_links",
            minimum=0,
        ),
        patterns=_compile_all(_str_tuple(data.get("regex"), "ad_filter.regex"), "ad_filter.regex"),
    )


def fold_keyword(value: str) -> str:
    return fold(value)


def _strip(data: dict) -> StripConfig:
    markers = tuple(
        fold(item) for item in _str_tuple(data.get("trailing_markers"), "strip.trailing_markers")
    )
    return StripConfig(
        patterns=_compile_all(_str_tuple(data.get("patterns"), "strip.patterns"), "strip.patterns"),
        trailing_markers=tuple(item for item in markers if item),
    )


def _links(data: dict) -> LinkConfig:
    params = frozenset(
        item.casefold() for item in _str_tuple(data.get("strip_params"), "links.strip_params")
    )
    rewrite_raw = data.get("domain_rewrite") or {}
    if not isinstance(rewrite_raw, dict):
        raise ConfigError("links.domain_rewrite должен быть словарём")
    rewrite: dict[str, str] = {}
    for source, target in rewrite_raw.items():
        if not isinstance(source, str) or not isinstance(target, str):
            raise ConfigError("links.domain_rewrite: ключи и значения должны быть строками")
        src = _host_key(source)
        dst = _host_key(target)
        if not src or not dst:
            raise ConfigError("links.domain_rewrite: пустой домен")
        rewrite[src] = dst
    blacklist = frozenset(
        _host_key(item) for item in _str_tuple(data.get("blacklist_domains"), "links.blacklist_domains")
    )
    blacklist = frozenset(item for item in blacklist if item)
    return LinkConfig(strip_params=params, domain_rewrite=rewrite, blacklist_domains=blacklist)


def _host_key(value: str) -> str:
    host = value.strip().casefold()
    if "://" in host:
        host = host.split("://", 1)[1]
    host = host.split("/")[0].split("@")[-1]
    if host.startswith("www."):
        host = host[4:]
    return host.split(":")[0]


def _rewrite(data: dict) -> RewriteConfig:
    temperature = data.get("temperature", 0.2)
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
        raise ConfigError("rewrite.temperature должен быть числом")
    if not 0 <= float(temperature) <= 2:
        raise ConfigError("rewrite.temperature должен быть от 0 до 2")
    return RewriteConfig(
        enabled=_bool(data.get("enabled"), "rewrite.enabled", default=True),
        tone=_text(data.get("tone", "нейтральный новостной"), "rewrite.tone"),
        max_length=_int(data.get("max_length", 900), "rewrite.max_length", minimum=1),
        keep_media_captions=_bool(
            data.get("keep_media_captions"),
            "rewrite.keep_media_captions",
            default=True,
        ),
        system_prompt=_text(data.get("system_prompt"), "rewrite.system_prompt"),
        temperature=float(temperature),
    )


def _dedupe(data: dict) -> DedupeConfig:
    threshold = _number(data.get("similarity_threshold", 0.72), "dedupe.similarity_threshold", minimum=0)
    if threshold > 1:
        raise ConfigError("dedupe.similarity_threshold должен быть от 0 до 1")
    return DedupeConfig(
        window_hours=_number(data.get("window_hours", 24), "dedupe.window_hours", minimum=0),
        similarity_threshold=threshold,
        min_tokens=_int(data.get("min_tokens", 6), "dedupe.min_tokens", minimum=1),
    )


def _rate_limit(data: dict) -> RateLimitConfig:
    return RateLimitConfig(
        min_interval_seconds=_number(
            data.get("min_interval_seconds", 3),
            "rate_limit.min_interval_seconds",
            minimum=0,
        ),
        max_posts_per_hour=_int(
            data.get("max_posts_per_hour", 30),
            "rate_limit.max_posts_per_hour",
            minimum=1,
        ),
    )


def _publish(data: dict) -> PublishConfig:
    album_max = _int(data.get("album_max_items", 10), "publish.album_max_items", minimum=1)
    if album_max > 10:
        raise ConfigError("publish.album_max_items не может быть больше 10 (лимит Telegram)")
    return PublishConfig(
        album_flush_seconds=_number(
            data.get("album_flush_seconds", 1.5),
            "publish.album_flush_seconds",
            minimum=0.2,
        ),
        album_max_items=album_max,
        caption_limit=_int(data.get("caption_limit", 1024), "publish.caption_limit", minimum=1),
        message_limit=_int(data.get("message_limit", 4096), "publish.message_limit", minimum=1),
    )
