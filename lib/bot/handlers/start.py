from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from lib.core.container import container


router = Router()

WELCOME_MESSAGE = """
<b>Привет! Я бот для создания дайджестов новостей.</b>

Я могу каждый день присылать тебе краткую сводку новостей из публичных Telegram-каналов по твоим интересам.

<b>Как начать:</b>
1. Укажи каналы командой /set_channels
2. Укажи интересы командой /set_interests
3. Получи дайджест командой /digest
4. Настрой автоматическую рассылку в /settings

<b>Команды:</b>
/set_channels — указать каналы для дайджеста
/add_channel — добавить канал
/remove_channel — удалить канал
/channels — показать каналы
/set_interests — указать интересы
/interests — показать интересы
/digest — получить дайджест сейчас
/settings — настройки рассылки
/help — помощь
"""


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if not message.from_user:
        return

    async with container.uow() as uow:
        await uow.users.get_or_create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
        )

    await message.answer(WELCOME_MESSAGE)
