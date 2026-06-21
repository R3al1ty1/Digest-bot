import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from lib.bot.handlers import channel, digest, help_cmd, interests, settings, start
from lib.core.container import container


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = container.logger


async def main() -> None:
    bot = Bot(
        token=container.settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    # Register routers
    dp.include_router(start.router)
    dp.include_router(channel.router)
    dp.include_router(interests.router)
    dp.include_router(digest.router)
    dp.include_router(settings.router)
    dp.include_router(help_cmd.router)

    container.db.init()
    logger.info("Starting bot...")

    try:
        await dp.start_polling(bot)
    finally:
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
