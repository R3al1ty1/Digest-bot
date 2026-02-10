from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from lib.db.database import async_session_maker
from lib.db.repositories import UserRepository
from lib.worker.tasks import generate_digest_task


router = Router()


@router.message(Command("digest"))
async def cmd_digest(message: Message) -> None:
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

    if not user.target_channel:
        await message.answer(
            "Сначала укажи канал для дайджеста командой /set_channel"
        )
        return

    await message.answer(
        f"Генерирую дайджест из канала <code>@{user.target_channel}</code>...\n\n"
        "Это может занять некоторое время."
    )

    # Send task to Celery
    generate_digest_task.delay(
        user_id=message.from_user.id,
        channel=user.target_channel,
    )
