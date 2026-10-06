from __future__ import annotations

from newsbot.config import (
    AdFilterConfig,
    Config,
    DedupeConfig,
    LinkConfig,
    PublishConfig,
    RateLimitConfig,
    RewriteConfig,
    SignatureConfig,
    StripConfig,
)


def make_config(
    *,
    ad_filter: AdFilterConfig | None = None,
    strip: StripConfig | None = None,
    links: LinkConfig | None = None,
    rewrite: RewriteConfig | None = None,
    signatures: SignatureConfig | None = None,
    dedupe: DedupeConfig | None = None,
) -> Config:
    return Config(
        target_channel="@your_news",
        log_channel="-1001234567890",
        owner_id=1,
        donors=(),
        signatures=signatures
        or SignatureConfig(
            default="channel",
            templates={
                "channel": "{channel}\n{hashtags}\n{channel_link}",
                "short": "{channel}",
            },
            channel_link="https://t.me/your_news",
            hashtags="#новости",
            channel_title="Новости",
        ),
        ad_filter=ad_filter
        or AdFilterConfig(
            keywords=("реклама", "erid", "промокод"),
            min_hits=1,
            max_external_links=3,
            patterns=(),
        ),
        strip=strip or StripConfig(patterns=(), trailing_markers=("подписывайтесь",)),
        links=links
        or LinkConfig(
            strip_params=frozenset({"fbclid"}),
            domain_rewrite={"old.news": "new.news"},
            blacklist_domains=frozenset({"ads.example"}),
        ),
        rewrite=rewrite
        or RewriteConfig(
            enabled=True,
            tone="нейтральный новостной",
            max_length=900,
            keep_media_captions=True,
            system_prompt="Перепиши новость, ничего не выдумывай.",
            temperature=0.2,
        ),
        dedupe=dedupe
        or DedupeConfig(window_hours=24, similarity_threshold=0.72, min_tokens=6),
        rate_limit=RateLimitConfig(min_interval_seconds=0, max_posts_per_hour=30),
        publish=PublishConfig(
            album_flush_seconds=1.5,
            album_max_items=10,
            caption_limit=1024,
            message_limit=4096,
        ),
    )
