from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class FingerprintRow:
    fingerprint: str
    normalized_text: str
    donor: str
    source_message_id: int
    created_at: str


@dataclass(frozen=True)
class ErrorRow:
    created_at: str
    context: str
    message: str


@dataclass(frozen=True)
class Preview:
    id: int
    donor: str
    source_message_ids: str
    log_chat_id: str
    log_message_id: int | None
    content_message_id: int | None
    kind: str
    text: str
    dedupe_text: str
    state: str
    target_message_ids: str | None
    edit_prompt_message_id: int | None
    created_at: str
    updated_at: str
    branch_name: str = ""
    target_channel: str = ""


@dataclass(frozen=True)
class PublishRow:
    created_at: str
    donor: str
    source_message_ids: str
    target_message_ids: str | None
    status: str
    reason: str


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def init(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS seen_messages (
                    donor TEXT NOT NULL,
                    message_id INTEGER NOT NULL,
                    seen_at TEXT NOT NULL,
                    PRIMARY KEY (donor, message_id)
                );
                CREATE TABLE IF NOT EXISTS fingerprints (
                    fingerprint TEXT PRIMARY KEY,
                    normalized_text TEXT NOT NULL,
                    donor TEXT NOT NULL,
                    source_message_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_fingerprints_created
                    ON fingerprints(created_at);
                CREATE TABLE IF NOT EXISTS publish_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    donor TEXT NOT NULL,
                    source_message_ids TEXT NOT NULL,
                    target_message_ids TEXT,
                    fingerprint TEXT,
                    status TEXT NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    context TEXT NOT NULL,
                    message TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runtime (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS previews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    donor TEXT NOT NULL,
                    source_message_ids TEXT NOT NULL,
                    log_chat_id TEXT NOT NULL,
                    log_message_id INTEGER,
                    content_message_id INTEGER,
                    kind TEXT NOT NULL DEFAULT 'text',
                    text TEXT NOT NULL,
                    dedupe_text TEXT NOT NULL DEFAULT '',
                    state TEXT NOT NULL,
                    target_message_ids TEXT,
                    edit_prompt_message_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_previews_state ON previews(state);
                CREATE TABLE IF NOT EXISTS preview_media (
                    preview_id INTEGER NOT NULL,
                    position INTEGER NOT NULL,
                    data BLOB NOT NULL,
                    PRIMARY KEY (preview_id, position)
                );
                """
            )
            self._add_column("previews", "branch_name", "TEXT NOT NULL DEFAULT ''")
            self._add_column("previews", "target_channel", "TEXT NOT NULL DEFAULT ''")
            self._conn.commit()

    def _add_column(self, table: str, column: str, definition: str) -> None:
        rows = self._conn.execute(f"PRAGMA table_info({table})").fetchall()
        names = {row[1] for row in rows}
        if column not in names:
            self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def mark_seen(self, donor: str, message_id: int, *, now: datetime | None = None) -> bool:
        """Return True when this donor message id is new."""
        with self._lock:
            cursor = self._conn.execute(
                """
                INSERT OR IGNORE INTO seen_messages(donor, message_id, seen_at)
                VALUES (?, ?, ?)
                """,
                (donor, message_id, iso(now or utcnow())),
            )
            self._conn.commit()
            return cursor.rowcount == 1

    def is_paused(self) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM runtime WHERE key = 'paused'"
            ).fetchone()
        return bool(row and row["value"] == "1")

    def set_paused(self, paused: bool) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO runtime(key, value) VALUES ('paused', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                ("1" if paused else "0",),
            )
            self._conn.commit()

    def save_fingerprint(
        self,
        fingerprint: str,
        normalized_text: str,
        donor: str,
        source_message_id: int,
        *,
        now: datetime | None = None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO fingerprints(
                    fingerprint, normalized_text, donor, source_message_id, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (fingerprint, normalized_text, donor, source_message_id, iso(now or utcnow())),
            )
            self._conn.commit()

    def fingerprints_since(self, since: datetime) -> list[FingerprintRow]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT fingerprint, normalized_text, donor, source_message_id, created_at
                FROM fingerprints
                WHERE created_at >= ?
                ORDER BY created_at ASC
                """,
                (iso(since),),
            ).fetchall()
        return [FingerprintRow(**dict(row)) for row in rows]

    def prune_fingerprints(self, before: datetime) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM fingerprints WHERE created_at < ?", (iso(before),))
            self._conn.commit()

    def log_publish(
        self,
        *,
        donor: str,
        source_message_ids: list[int],
        target_message_ids: list[int] | None,
        fingerprint: str,
        status: str,
        reason: str = "",
        now: datetime | None = None,
    ) -> None:
        targets = ",".join(str(item) for item in target_message_ids) if target_message_ids else None
        sources = ",".join(str(item) for item in source_message_ids)
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO publish_log(
                    donor, source_message_ids, target_message_ids, fingerprint,
                    status, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    donor,
                    sources,
                    targets,
                    fingerprint,
                    status,
                    reason,
                    iso(now or utcnow()),
                ),
            )
            self._conn.commit()

    def recent_publishes(self, limit: int = 5) -> list[PublishRow]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT created_at, donor, source_message_ids, target_message_ids, status, reason
                FROM publish_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            PublishRow(
                created_at=row["created_at"],
                donor=row["donor"],
                source_message_ids=row["source_message_ids"],
                target_message_ids=row["target_message_ids"],
                status=row["status"],
                reason=row["reason"],
            )
            for row in rows
        ]

    def add_error(self, context: str, message: str, *, now: datetime | None = None) -> None:
        text = message.strip()
        if len(text) > 1000:
            text = text[:1000]
        with self._lock:
            self._conn.execute(
                "INSERT INTO errors(created_at, context, message) VALUES (?, ?, ?)",
                (iso(now or utcnow()), context, text),
            )
            self._conn.commit()

    def recent_errors(self, limit: int = 5) -> list[ErrorRow]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT created_at, context, message
                FROM errors
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [ErrorRow(row["created_at"], row["context"], row["message"]) for row in rows]

    def create_preview(
        self,
        *,
        donor: str,
        source_message_ids: list[int],
        log_chat_id: str,
        text: str,
        dedupe_text: str,
        branch_name: str = "",
        target_channel: str = "",
        now: datetime | None = None,
    ) -> int:
        moment = iso(now or utcnow())
        sources = ",".join(str(item) for item in source_message_ids)
        with self._lock:
            cursor = self._conn.execute(
                """
                INSERT INTO previews(
                    donor, source_message_ids, log_chat_id, text, dedupe_text,
                    state, created_at, updated_at, branch_name, target_channel
                ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
                """,
                (
                    donor,
                    sources,
                    log_chat_id,
                    text,
                    dedupe_text,
                    moment,
                    moment,
                    branch_name,
                    target_channel,
                ),
            )
            self._conn.commit()
            return int(cursor.lastrowid)

    def attach_preview_message(
        self,
        preview_id: int,
        *,
        log_message_id: int,
        content_message_id: int,
        kind: str,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                UPDATE previews
                SET log_message_id = ?, content_message_id = ?, kind = ?, updated_at = ?
                WHERE id = ?
                """,
                (log_message_id, content_message_id, kind, iso(utcnow()), preview_id),
            )
            self._conn.commit()

    def save_preview_media(self, preview_id: int, blobs: list[bytes]) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM preview_media WHERE preview_id = ?", (preview_id,))
            self._conn.executemany(
                "INSERT INTO preview_media(preview_id, position, data) VALUES (?, ?, ?)",
                [(preview_id, index, blob) for index, blob in enumerate(blobs)],
            )
            self._conn.commit()

    def preview_media(self, preview_id: int) -> list[bytes]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT data FROM preview_media
                WHERE preview_id = ?
                ORDER BY position ASC
                """,
                (preview_id,),
            ).fetchall()
        return [bytes(row["data"]) for row in rows]

    def get_preview(self, preview_id: int) -> Preview | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM previews WHERE id = ?", (preview_id,)).fetchone()
        if row is None:
            return None
        return _preview_from_row(row)

    def replace_preview_text(self, preview_id: int, text: str) -> bool:
        with self._lock:
            cursor = self._conn.execute(
                """
                UPDATE previews
                SET text = ?, updated_at = ?
                WHERE id = ? AND state = 'pending'
                """,
                (text, iso(utcnow()), preview_id),
            )
            self._conn.commit()
            return cursor.rowcount == 1

    def transition_preview(
        self,
        preview_id: int,
        new_state: str,
        *,
        expect: str,
        target_message_ids: list[int] | None = None,
    ) -> bool:
        if new_state not in {"pending", "sent", "rejected"}:
            raise ValueError(new_state)
        targets = None
        if target_message_ids is not None:
            targets = ",".join(str(item) for item in target_message_ids)
        with self._lock:
            cursor = self._conn.execute(
                """
                UPDATE previews
                SET state = ?, target_message_ids = COALESCE(?, target_message_ids), updated_at = ?
                WHERE id = ? AND state = ?
                """,
                (new_state, targets, iso(utcnow()), preview_id, expect),
            )
            self._conn.commit()
            return cursor.rowcount == 1

    def set_edit_prompt(self, preview_id: int, message_id: int) -> bool:
        with self._lock:
            cursor = self._conn.execute(
                """
                UPDATE previews
                SET edit_prompt_message_id = ?, updated_at = ?
                WHERE id = ? AND state = 'pending'
                """,
                (message_id, iso(utcnow()), preview_id),
            )
            self._conn.commit()
            return cursor.rowcount == 1

    def clear_edit_prompt(self, preview_id: int) -> None:
        with self._lock:
            self._conn.execute(
                """
                UPDATE previews
                SET edit_prompt_message_id = NULL, updated_at = ?
                WHERE id = ?
                """,
                (iso(utcnow()), preview_id),
            )
            self._conn.commit()

    def pending_edit_prompts(self) -> list[tuple[int, int | None]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, edit_prompt_message_id
                FROM previews
                WHERE state = 'pending' AND edit_prompt_message_id IS NOT NULL
                ORDER BY id ASC
                """
            ).fetchall()
        return [(int(row["id"]), int(row["edit_prompt_message_id"])) for row in rows]

    def pending_review_messages(self) -> list[tuple[int, int | None, int | None]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, log_message_id, content_message_id
                FROM previews
                WHERE state = 'pending'
                ORDER BY id ASC
                """
            ).fetchall()
        return [
            (
                int(row["id"]),
                int(row["log_message_id"]) if row["log_message_id"] is not None else None,
                int(row["content_message_id"]) if row["content_message_id"] is not None else None,
            )
            for row in rows
        ]

    def backfill_preview_channels(self, branch_name: str, target_channel: str) -> None:
        """Old previews belong to the feed that existed before branches."""
        with self._lock:
            self._conn.execute(
                """
                UPDATE previews
                SET branch_name = ?, target_channel = ?
                WHERE branch_name = '' AND target_channel = ''
                """,
                (branch_name, target_channel),
            )
            self._conn.commit()

    def count_pending_previews(self) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM previews WHERE state = 'pending'"
            ).fetchone()
        return int(row["n"])


def _preview_from_row(row: sqlite3.Row) -> Preview:
    return Preview(
        id=int(row["id"]),
        donor=row["donor"],
        source_message_ids=row["source_message_ids"],
        log_chat_id=row["log_chat_id"],
        log_message_id=int(row["log_message_id"]) if row["log_message_id"] is not None else None,
        content_message_id=int(row["content_message_id"]) if row["content_message_id"] is not None else None,
        kind=row["kind"],
        text=row["text"],
        dedupe_text=row["dedupe_text"],
        state=row["state"],
        target_message_ids=row["target_message_ids"],
        edit_prompt_message_id=(
            int(row["edit_prompt_message_id"]) if row["edit_prompt_message_id"] is not None else None
        ),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        branch_name=row["branch_name"] if "branch_name" in row.keys() else "",
        target_channel=row["target_channel"] if "target_channel" in row.keys() else "",
    )
