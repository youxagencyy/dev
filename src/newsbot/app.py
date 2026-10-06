from __future__ import annotations

import asyncio
import logging
import signal

import httpx
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from telethon import TelegramClient

from newsbot.collector import Collector
from newsbot.commands import build_router
from newsbot.config import load_config, load_settings
from newsbot.db import Database
from newsbot.dedupe import Deduper
from newsbot.pipeline import Pipeline
from newsbot.publisher import Publisher
from newsbot.rate_limit import RateLimiter
from newsbot.rewrite import Rewriter
from newsbot.runtime import Runtime
from newsbot.session import open_session

logger = logging.getLogger("newsbot")


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("telethon").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


async def async_main() -> None:
    setup_logging()
    settings = load_settings()
    config = load_config(settings.config_path)
    db = Database(settings.database_path)
    db.init()
    http = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))
    bot: Bot | None = None
    client: TelegramClient | None = None
    collector: Collector | None = None
    dispatcher: Dispatcher | None = None
    publisher: Publisher | None = None
    publisher_started = False
    tasks: list[asyncio.Task[object]] = []
    try:
        rewriter = Rewriter(
            config.rewrite,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
            client=http,
        )
        if rewriter.active:
            logger.info("рерайт включён")
        else:
            logger.warning(
                "OPENAI_API_KEY не задан или rewrite.enabled=false: "
                "рерайт пропускается, публикуется очищенный текст"
            )
        deduper = Deduper(db, config.dedupe)
        pipeline = Pipeline(config, db, deduper, rewriter)
        bot = Bot(token=settings.bot_token)
        publisher = Publisher(
            bot,
            config,
            db,
            RateLimiter(
                config.rate_limit.min_interval_seconds,
                config.rate_limit.max_posts_per_hour,
            ),
        )
        client = TelegramClient(
            open_session(settings.session, settings.database_path),
            settings.api_id,
            settings.api_hash,
        )
        await client.connect()
        if not await client.is_user_authorized():
            raise SystemExit(
                "Сессия Telegram не авторизована. Локально выполните "
                "python -m newsbot.login и запишите строку в TELEGRAM_SESSION. "
                "Строку сессии не коммитьте."
            )
        collector = Collector(client, config, db, pipeline, publisher)
        runtime = Runtime(config, db, pipeline, publisher, client)
        dispatcher = Dispatcher()
        dispatcher.include_router(build_router(runtime))
        await bot.set_my_commands(
            [
                BotCommand(command="status", description="Состояние, очередь, ошибки"),
                BotCommand(command="pause", description="Пауза публикации"),
                BotCommand(command="resume", description="Продолжить публикацию"),
                BotCommand(command="donors", description="Список доноров"),
                BotCommand(command="preview", description="Предпросмотр без публикации"),
            ]
        )
        await collector.start()
        enabled = [donor.username for donor in config.donors if donor.enabled]
        logger.info(
            "newsbot started target=%s donors=%s",
            config.target_channel,
            ",".join(enabled) or "-",
        )
        publisher_task = asyncio.create_task(publisher.worker(), name="publisher")
        publisher_started = True
        polling_task = asyncio.create_task(
            dispatcher.start_polling(bot, handle_signals=False),
            name="polling",
        )
        telethon_task = asyncio.create_task(client.run_until_disconnected(), name="telethon")
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop.set)
            except NotImplementedError:
                pass
        stop_task = asyncio.create_task(stop.wait(), name="stop")
        tasks = [publisher_task, polling_task, telethon_task, stop_task]
        done, _pending = await asyncio.wait(set(tasks), return_when=asyncio.FIRST_COMPLETED)
        if stop_task not in done:
            for task in done:
                if task.cancelled():
                    continue
                error = task.exception()
                if error:
                    logger.error("task stopped: %s", error.__class__.__name__)
    finally:
        if dispatcher is not None:
            await dispatcher.stop_polling()
        if collector is not None:
            await collector.stop()
        if publisher is not None and publisher_started:
            await publisher.stop()
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if client is not None:
            await client.disconnect()
        if bot is not None:
            await bot.session.close()
        await http.aclose()
        db.close()
        logger.info("newsbot stopped")


def main() -> None:
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass
