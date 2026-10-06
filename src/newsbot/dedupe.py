from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

from newsbot.config import DedupeConfig
from newsbot.db import Database, utcnow
from newsbot.textutil import content_tokens, normalize_for_fingerprint


def fingerprint(normalized: str) -> str:
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


class Deduper:
    """Exact fingerprint plus token Jaccard inside a time window.

    The fingerprint is a hash of normalized words (lowercase, ``ё``→``е``,
    URLs and punctuation removed). Short texts (fewer than ``min_tokens``
    words of length ≥ 3) match only on the exact fingerprint, so two brief
    unrelated headlines do not collapse together. Similarity is the Jaccard
    index of those tokens and fires at ``similarity_threshold``.
    """

    def __init__(self, db: Database, config: DedupeConfig) -> None:
        self.db = db
        self.window_hours = config.window_hours
        self.threshold = config.similarity_threshold
        self.min_tokens = config.min_tokens

    def is_duplicate(self, text: str, *, now: datetime | None = None) -> tuple[bool, str]:
        normalized = normalize_for_fingerprint(text)
        if not normalized:
            return False, ""
        current = fingerprint(normalized)
        moment = now or utcnow()
        since = moment - timedelta(hours=self.window_hours)
        tokens = content_tokens(normalized)
        for row in self.db.fingerprints_since(since):
            if row.fingerprint == current:
                return True, "exact fingerprint"
            if len(tokens) < self.min_tokens:
                continue
            other = content_tokens(row.normalized_text)
            if len(other) < self.min_tokens:
                continue
            score = jaccard(tokens, other)
            if score >= self.threshold:
                return True, f"similar {score:.2f}"
        return False, ""

    def remember(
        self,
        text: str,
        *,
        donor: str,
        message_id: int,
        now: datetime | None = None,
    ) -> str:
        normalized = normalize_for_fingerprint(text)
        if not normalized:
            return ""
        moment = now or utcnow()
        if self.window_hours > 0:
            self.db.prune_fingerprints(moment - timedelta(hours=self.window_hours))
        digest = fingerprint(normalized)
        self.db.save_fingerprint(digest, normalized, donor, message_id, now=moment)
        return digest
