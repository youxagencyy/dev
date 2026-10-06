from __future__ import annotations

from pathlib import Path

from telethon.sessions import StringSession


def open_session(session_value: str, database_path: str) -> StringSession | str:
    """String session from env, a file path, or ``<db dir>/newsbot``."""
    value = (session_value or "").strip()
    if not value:
        return str(Path(database_path).parent / "newsbot")
    if _looks_like_path(value):
        path = Path(value)
        if path.name.endswith(".session"):
            path = path.with_suffix("")
        return str(path)
    return StringSession(value)


def _looks_like_path(value: str) -> bool:
    # String sessions are urlsafe base64 (version prefix + alphabet without '/').
    return "/" in value or value.endswith(".session")
