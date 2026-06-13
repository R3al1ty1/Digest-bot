from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from lib.core.container import container
from lib.worker.tasks import generate_digest_task


router = Router()


@router.message(Command("digest"))
async def cmd_digest(message: Message) -> None:
    if not message.from_user:
        return

    async with container.uow() as uow:
        user = await uow.users.get_by_id(message.from_user.id)
        channels = await uow.user_channels.list_active_by_user(message.from_user.id)
        interests = await uow.digest_interests.list_by_user(message.from_user.id)

    if not user:
        await message.answer(
            "Ты ещё не зарегистрирован. Нажми /start для начала."
        )
        return

    if not channels:
        await message.answer(
            "Сначала укажи каналы для дайджеста командой /set_channels"
        )
        return

    if not interests:
        await message.answer(
            "Сначала укажи интересы для дайджеста командой /set_interests"
        )
        return

    await message.answer(
        f"Генерирую дайджест из {len(channels)} каналов по {len(interests)} интересам...\n\n"
        "Это может занять некоторое время."
    )

    generate_digest_task.delay(
        user_id=message.from_user.id,
        channels=[item.channel for item in channels],
        interests=[item.interest for item in interests],
    )
