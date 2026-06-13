from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from lib.core.container import container


router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    if not message.from_user:
        return

    async with container.uow() as uow:
        user = await uow.users.get_by_id(message.from_user.id)

    if not user:
        await message.answer(
            "Ты ещё не зарегистрирован. Нажми /start для начала."
        )
        return

    await message.answer(
        """
<b>Помощь по использованию бота:</b>
<b>Как начать:</b>
1. Укажи каналы командой /set_channels
2. Укажи интересы командой /set_interests
3. Получи дайджест командой /digest
4. Настрой автоматическую рассылку в /settings

<b>Команды:</b>
/set_channels @channel_one @channel_two — заменить список каналов
/add_channel @channel_three — добавить канал
/remove_channel @channel_one — удалить канал
/channels — показать текущие каналы
/set_interests финансы, технологии — заменить список интересов
/interests — показать текущие интересы
/digest — получить дайджест сейчас
/settings — настройки рассылки
/help — помощь
        """
    )
