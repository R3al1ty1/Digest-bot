from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from lib.core.container import container
from lib.services.channels import (
    ChannelUpdateResult,
    ChannelValidationError,
    filter_accessible_channels,
    normalize_channel_username,
    parse_channel_list,
    validate_channel_username_format,
)


router = Router()


class SetChannelState(StatesGroup):
    waiting_for_channel = State()


@router.message(Command("set_channel"))
async def cmd_set_channel(message: Message, state: FSMContext) -> None:
    if message.text and len(message.text.split()) > 1:
        channel = message.text.split(maxsplit=1)[1].strip()
        await _process_channel(message, state, channel)
        return

    await state.set_state(SetChannelState.waiting_for_channel)
    await message.answer(
        "Отправь мне юзернейм канала (например, <code>durov</code> или <code>@durov</code>).\n\n"
        "Канал должен быть публичным."
    )


@router.message(Command("set_channels"))
async def cmd_set_channels(message: Message) -> None:
    if not message.text:
        return

    raw_channels = message.text.partition(" ")[2]
    if not raw_channels:
        await message.answer(
            "Укажи каналы после команды.\n\n"
            "Пример: /set_channels @channel_one @channel_two"
        )
        return

    await _replace_channels(message, raw_channels)


@router.message(Command("add_channel"))
async def cmd_add_channel(message: Message) -> None:
    if not message.from_user or not message.text:
        return

    raw_channel = message.text.partition(" ")[2]
    if not raw_channel:
        await message.answer(
            "Укажи канал после команды.\n\n"
            "Пример: /add_channel @channel_one"
        )
        return

    try:
        channel = normalize_channel_username(raw_channel)
        validate_channel_username_format(channel)
    except ChannelValidationError:
        await message.answer("Некорректный юзернейм канала. Попробуй ещё раз.")
        return

    async with container.uow() as uow:
        existing = await uow.user_channels.list_active_by_user(message.from_user.id)
        existing_channels = {item.channel.lower() for item in existing}

        if channel.lower() in existing_channels:
            await message.answer(f"Канал <code>@{channel}</code> уже добавлен.")
            return

        if len(existing) >= 5:
            await message.answer("Можно добавить максимум 5 каналов.")
            return

    await message.answer("Проверяю доступ к каналу...")

    try:
        result = await filter_accessible_channels([channel])
    except ChannelValidationError:
        await message.answer(
            f"Не удалось получить доступ к каналу <code>@{channel}</code>."
        )
        return

    async with container.uow() as uow:
        await uow.user_channels.add_channel(
            message.from_user.id,
            result.saved_channels[0],
        )

    await message.answer(f"Канал <code>@{channel}</code> добавлен.")


@router.message(Command("remove_channel"))
async def cmd_remove_channel(message: Message) -> None:
    if not message.from_user or not message.text:
        return

    raw_channel = message.text.partition(" ")[2]
    if not raw_channel:
        await message.answer(
            "Укажи канал после команды.\n\n"
            "Пример: /remove_channel @channel_one"
        )
        return

    try:
        channel = normalize_channel_username(raw_channel)
        validate_channel_username_format(channel)
    except ChannelValidationError:
        await message.answer("Некорректный юзернейм канала. Попробуй ещё раз.")
        return

    async with container.uow() as uow:
        removed = await uow.user_channels.remove_channel(
            message.from_user.id,
            channel,
        )

    if not removed:
        await message.answer(f"Канал <code>@{channel}</code> не найден в списке.")
        return

    await message.answer(f"Канал <code>@{channel}</code> удалён.")


@router.message(Command("channels"))
async def cmd_channels(message: Message) -> None:
    if not message.from_user:
        return

    async with container.uow() as uow:
        channels = await uow.user_channels.list_active_by_user(message.from_user.id)

    if not channels:
        await message.answer(
            "Каналы ещё не настроены.\n\n"
            "Пример: /set_channels @channel_one @channel_two"
        )
        return

    items = "\n".join(f"• <code>@{item.channel}</code>" for item in channels)
    await message.answer(f"<b>Твои каналы:</b>\n\n{items}")


@router.message(SetChannelState.waiting_for_channel, F.text)
async def process_channel_input(message: Message, state: FSMContext) -> None:
    if not message.text:
        return

    channel = message.text.strip()
    await _process_channel(message, state, channel)


async def _process_channel(message: Message, state: FSMContext, channel: str) -> None:
    await _replace_channels(message, channel)
    await state.clear()


async def _replace_channels(message: Message, raw_channels: str) -> None:
    if not message.from_user:
        return

    try:
        channels = parse_channel_list(raw_channels)
    except ChannelValidationError as e:
        await _answer_channel_validation_error(message, str(e))
        return

    await message.answer("Проверяю доступ к каналам...")

    try:
        result = await filter_accessible_channels(channels)
    except ChannelValidationError as e:
        await _answer_channel_validation_error(message, str(e))
        return

    async with container.uow() as uow:
        await uow.user_channels.replace_for_user(
            message.from_user.id,
            result.saved_channels,
        )
        await uow.users.update_channel(
            message.from_user.id,
            result.saved_channels[0],
        )

    await message.answer(_format_channel_update_result(result))


def _format_channel_update_result(result: ChannelUpdateResult) -> str:
    saved = "\n".join(f"• <code>@{channel}</code>" for channel in result.saved_channels)
    text = (
        "<b>Каналы сохранены:</b>\n\n"
        f"{saved}\n\n"
        "Теперь задай интересы командой /set_interests или получи дайджест командой /digest."
    )

    if result.skipped_channels:
        skipped = "\n".join(
            f"• <code>@{item.channel}</code> — недоступен"
            for item in result.skipped_channels
        )
        text += f"\n\n<b>Не удалось добавить:</b>\n{skipped}"

    return text


async def _answer_channel_validation_error(message: Message, error: str) -> None:
    if error == "empty_channels":
        await message.answer(
            "Укажи хотя бы один канал.\n\n"
            "Пример: /set_channels @channel_one @channel_two"
        )
        return

    if error == "too_many_channels":
        await message.answer("Можно добавить максимум 5 каналов.")
        return

    if error == "all_channels_not_accessible":
        await message.answer(
            "Не удалось получить доступ ни к одному каналу.\n\n"
            "Убедись, что каналы существуют, публичные и указаны правильно."
        )
        return

    await message.answer("Некорректный юзернейм канала. Попробуй ещё раз.")
