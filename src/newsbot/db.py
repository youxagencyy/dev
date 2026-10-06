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
                """
            )
            self._conn.commit()

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
