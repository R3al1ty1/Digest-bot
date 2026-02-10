from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from lib.db.database import async_session_maker
from lib.db.repositories import UserRepository


router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    if not message.from_user:
        return

    async with async_session_maker() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(message.from_user.id)

    if not user:
        await message.answer(
            "Ты ещё не зарегистрирован. Нажми /start для начала."
        )
        return

    await message.answer(
        """
<b>Помощь по использованию бота:</b>
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
    )
