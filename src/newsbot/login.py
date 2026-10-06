"""Store a Telethon user session in gitignored .env.

Asks for the phone, the login code, and, when the account has a cloud
password, that password. A correct code plus SessionPasswordNeededError
is the password step, not a rejected code. The session string is written
only to TELEGRAM_SESSION and is not printed.
"""

from __future__ import annotations

import asyncio
import getpass
import os
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import PhoneCodeInvalidError, SessionPasswordNeededError
from telethon.sessions import StringSession

# Port 443 on this network answers HTTP 400. Telegram also accepts 5222.
DC_PORT = 5222


def sign_in_outcome(exc: BaseException) -> str:
    """Distinguish a cloud-password challenge from a rejected code."""
    if isinstance(exc, SessionPasswordNeededError):
        return "password"
    if isinstance(exc, PhoneCodeInvalidError):
        return "bad_code"
    return "error"


def write_session_env(session: str, path: Path | None = None) -> None:
    target = path or Path(os.getenv("ENV_FILE", ".env"))
    lines = target.read_text(encoding="utf-8").splitlines() if target.is_file() else []
    updated: list[str] = []
    found = False
    for line in lines:
        if line.startswith("TELEGRAM_SESSION="):
            updated.append("TELEGRAM_SESSION=" + session)
            found = True
        else:
            updated.append(line)
    if not found:
        updated.append("TELEGRAM_SESSION=" + session)
    target.write_text("\n".join(updated) + "\n", encoding="utf-8")
    os.chmod(target, 0o600)


async def _login() -> None:
    api_id_raw = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    if not api_id_raw.isdigit() or not api_hash:
        raise SystemExit("Задайте TELEGRAM_API_ID и TELEGRAM_API_HASH в окружении")
    client = TelegramClient(StringSession(), int(api_id_raw), api_hash)
    original_set_dc = client.session.set_dc

    def set_dc(dc_id, server_address, port):
        return original_set_dc(dc_id, server_address, DC_PORT)

    client.session.set_dc = set_dc  # type: ignore[method-assign]
    client.session.set_dc(2, "149.154.167.91", DC_PORT)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            phone = input("Please enter your phone (or bot token): ").strip()
            await client.send_code_request(phone)
            code = input("Please enter the code you received: ").strip()
            try:
                await client.sign_in(phone=phone, code=code)
            except Exception as exc:
                outcome = sign_in_outcome(exc)
                if outcome == "bad_code":
                    raise SystemExit("код не принят") from exc
                if outcome != "password":
                    raise
                print("2FA password required", flush=True)
                password = getpass.getpass("")
                if not password:
                    raise SystemExit("пароль не задан")
                await client.sign_in(password=password)
        write_session_env(client.session.save())
        print("TELEGRAM_SESSION written to .env", flush=True)
    finally:
        await client.disconnect()


def main() -> None:
    asyncio.run(_login())


if __name__ == "__main__":
    main()
