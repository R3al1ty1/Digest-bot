from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from lib.db.database import async_session_maker
from lib.db.repositories import UserRepository
from lib.worker.scraper import test_channel_access


router = Router()


class SetChannelState(StatesGroup):
    waiting_for_channel = State()


@router.message(Command("set_channel"))
async def cmd_set_channel(message: Message, state: FSMContext) -> None:
    # Check if channel provided as argument
    if message.text and len(message.text.split()) > 1:
        channel = message.text.split(maxsplit=1)[1].strip()
        await _process_channel(message, state, channel)
        return

    await state.set_state(SetChannelState.waiting_for_channel)
    await message.answer(
        "Отправь мне юзернейм канала (например, <code>durov</code> или <code>@durov</code>).\n\n"
        "Канал должен быть публичным."
    )


@router.message(SetChannelState.waiting_for_channel, F.text)
async def process_channel_input(message: Message, state: FSMContext) -> None:
    if not message.text:
        return

    channel = message.text.strip()
    await _process_channel(message, state, channel)


async def _process_channel(message: Message, state: FSMContext, channel: str) -> None:
    if not message.from_user:
        return

    channel = channel.lstrip("@").strip()

    if not channel:
        await message.answer("Некорректный юзернейм канала. Попробуй ещё раз.")
        return

    # Validate channel
    await message.answer("Проверяю доступ к каналу...")

    is_accessible = await test_channel_access(channel)

    if not is_accessible:
        await message.answer(
            f"Не удалось получить доступ к каналу <code>{channel}</code>.\n\n"
            "Убедись, что:\n"
            "• Канал существует\n"
            "• Канал публичный\n"
            "• Юзернейм указан правильно"
        )
        return

    # Save to database
    async with async_session_maker() as session:
        repo = UserRepository(session)
        await repo.update_channel(message.from_user.id, channel)

    await state.clear()
    await message.answer(
        f"Канал <code>@{channel}</code> успешно установлен!\n\n"
        "Теперь можешь получить дайджест командой /digest"
    )
