from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from lib.core.container import container
from lib.services.interests import InterestValidationError, parse_interest_list


router = Router()


@router.message(Command("set_interests"))
async def cmd_set_interests(message: Message) -> None:
    if not message.from_user or not message.text:
        return

    raw_interests = message.text.partition(" ")[2]
    if not raw_interests:
        await message.answer(
            "Укажи интересы после команды.\n\n"
            "Пример: /set_interests финансы, технологии, здоровье"
        )
        return

    try:
        interests = parse_interest_list(raw_interests)
    except InterestValidationError as e:
        await _answer_interest_validation_error(message, str(e))
        return

    async with container.uow() as uow:
        await uow.digest_interests.replace_for_user(
            message.from_user.id,
            interests,
        )

    items = "\n".join(f"• {interest}" for interest in interests)
    await message.answer(
        "<b>Интересы сохранены:</b>\n\n"
        f"{items}\n\n"
        "Теперь можешь получить дайджест командой /digest."
    )


@router.message(Command("interests"))
async def cmd_interests(message: Message) -> None:
    if not message.from_user:
        return

    async with container.uow() as uow:
        interests = await uow.digest_interests.list_by_user(message.from_user.id)

    if not interests:
        await message.answer(
            "Интересы ещё не настроены.\n\n"
            "Пример: /set_interests финансы, технологии, здоровье"
        )
        return

    items = "\n".join(f"• {item.interest}" for item in interests)
    await message.answer(f"<b>Твои интересы:</b>\n\n{items}")


async def _answer_interest_validation_error(message: Message, error: str) -> None:
    if error == "empty_interests":
        await message.answer(
            "Укажи хотя бы один интерес.\n\n"
            "Пример: /set_interests финансы, технологии, здоровье"
        )
        return

    if error == "too_many_interests":
        await message.answer("Можно добавить максимум 5 интересов.")
        return

    await message.answer(
        "Некорректный интерес. Используй текст до 100 символов."
    )
