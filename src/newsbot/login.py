"""Print a Telethon StringSession for TELEGRAM_SESSION.

The printed string is a secret. Put it in .env and do not commit it.
The session is only for reading the public donor channels from config.yaml.
"""

from __future__ import annotations

import asyncio
import os

from telethon import TelegramClient
from telethon.sessions import StringSession


async def _login() -> None:
    api_id_raw = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    if not api_id_raw.isdigit() or not api_hash:
        raise SystemExit("Задайте TELEGRAM_API_ID и TELEGRAM_API_HASH в окружении")
    client = TelegramClient(StringSession(), int(api_id_raw), api_hash)
    await client.start()
    session = client.session.save()
    await client.disconnect()
    print(session)


def main() -> None:
    asyncio.run(_login())


if __name__ == "__main__":
    main()
