import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from lib.bot.handlers import channel, digest, settings, start
from lib.core.config import settings as app_settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(
        token=app_settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    # Register routers
    dp.include_router(start.router)
    dp.include_router(channel.router)
    dp.include_router(digest.router)
    dp.include_router(settings.router)

    logger.info("Starting bot...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
