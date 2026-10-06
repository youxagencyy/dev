from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from newsbot.ad_filter import is_advertisement
from newsbot.config import Config
from newsbot.db import Database
from newsbot.dedupe import Deduper, fingerprint
from newsbot.links import rewrite_links
from newsbot.rewrite import RewriteClient
from newsbot.signatures import append_signature, strip_donor_marks
from newsbot.textutil import fit_text, normalize_for_fingerprint, prepare_text

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PostInput:
    donor: str
    message_id: int
    text: str
    is_service: bool
    has_photo: bool
    signature_template: str | None = None


@dataclass(frozen=True)
class PipelineResult:
    action: str
    reason: str
    text: str
    fingerprint: str
    dedupe_text: str = ""


class Pipeline:
    """Clean → rewrite → dedupe → signature.

    Dedupe uses the cleaned text (stable across donors) and, when the model
    changes the wording, the rewritten text as well. ``record=False`` (preview)
    does not write fingerprints.
    """

    def __init__(
        self,
        config: Config,
        db: Database,
        deduper: Deduper,
        rewriter: RewriteClient,
    ) -> None:
        self.config = config
        self.db = db
        self.deduper = deduper
        self.rewriter = rewriter
        self._lock = asyncio.Lock()

    async def run(self, post: PostInput, *, record: bool) -> PipelineResult:
        cleaned = self._clean(post)
        if isinstance(cleaned, PipelineResult):
            return cleaned

        if cleaned.strip():
            duplicate, reason = self.deduper.is_duplicate(cleaned)
            if duplicate:
                return self._duplicate(cleaned, reason)

        body, error = await self._rewrite(post, cleaned)
        if error:
            logger.warning("rewrite failed, publishing cleaned text: %s", error)
            self.db.add_error("rewrite", error)

        async with self._lock:
            if cleaned.strip():
                duplicate, reason = self.deduper.is_duplicate(cleaned)
                if duplicate:
                    return self._duplicate(cleaned, reason)
            if body.strip() and normalize_for_fingerprint(body) != normalize_for_fingerprint(cleaned):
                duplicate, reason = self.deduper.is_duplicate(body)
                if duplicate:
                    return self._duplicate(body, reason)
            digest = ""
            if record and cleaned.strip():
                digest = self.deduper.remember(
                    cleaned,
                    donor=post.donor,
                    message_id=post.message_id,
                )
            if (
                record
                and body.strip()
                and normalize_for_fingerprint(body) != normalize_for_fingerprint(cleaned)
            ):
                self.deduper.remember(body, donor=post.donor, message_id=post.message_id)
            if not digest and cleaned.strip():
                digest = fingerprint(normalize_for_fingerprint(cleaned))
            limit = (
                self.config.publish.caption_limit
                if post.has_photo
                else self.config.publish.message_limit
            )
            text = append_signature(body, self.config.signatures, post.signature_template)
            text = fit_text(text, limit)
            return PipelineResult("publish", "", text, digest, cleaned)

    def _clean(self, post: PostInput) -> str | PipelineResult:
        if post.is_service:
            return PipelineResult("skip", "service", "", "")
        raw = prepare_text(post.text)
        if not raw and not post.has_photo:
            return PipelineResult("skip", "empty", "", "")
        rejected, reason = is_advertisement(raw, self.config.ad_filter)
        if rejected:
            return PipelineResult("skip", reason, "", "")
        cleaned = strip_donor_marks(raw, self.config.strip)
        cleaned = rewrite_links(cleaned, self.config.links)
        if post.has_photo and not self.config.rewrite.keep_media_captions:
            cleaned = ""
        if not cleaned.strip() and not post.has_photo:
            return PipelineResult("skip", "empty_after_clean", "", "")
        return cleaned

    async def _rewrite(self, post: PostInput, cleaned: str) -> tuple[str, str | None]:
        if not cleaned.strip():
            return "", None
        if post.has_photo and not self.config.rewrite.keep_media_captions:
            return "", None
        if not self.rewriter.active:
            return cleaned, None
        return await self.rewriter.rewrite(cleaned)

    def _duplicate(self, text: str, reason: str) -> PipelineResult:
        digest = fingerprint(normalize_for_fingerprint(text))
        return PipelineResult("duplicate", reason, "", digest)
