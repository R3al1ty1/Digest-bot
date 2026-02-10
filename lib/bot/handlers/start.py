from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from lib.db.database import async_session_maker
from lib.db.repositories import UserRepository


router = Router()

WELCOME_MESSAGE = """
<b>Привет! Я бот для создания дайджестов новостей.</b>

Я могу каждый день присылать тебе краткую сводку новостей из любого публичного Telegram-канала.

<b>Как начать:</b>
1. Укажи канал командой /set_channel
2. Получи дайджест командой /digest
3. Настрой автоматическую рассылку в /settings

<b>Команды:</b>
/set_channel — указать канал для дайджеста
/digest — получить дайджест сейчас
/settings — настройки рассылки
/help — помощь
"""


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if not message.from_user:
        return

    async with async_session_maker() as session:
        repo = UserRepository(session)
        await repo.get_or_create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
        )

    await message.answer(WELCOME_MESSAGE)
