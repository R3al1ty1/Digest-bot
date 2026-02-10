from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from lib.bot.keyboards import get_settings_keyboard, get_time_keyboard
from lib.db.database import async_session_maker
from lib.db.repositories import UserRepository


router = Router()


class SettingsState(StatesGroup):
    waiting_for_time = State()


def _format_settings(user) -> str:
    channel = f"@{user.target_channel}" if user.target_channel else "не указан"
    schedule = user.schedule_time.strftime("%H:%M") if user.schedule_time else "09:00"
    status = "включена" if user.is_active else "выключена"

    return (
        "<b>Текущие настройки:</b>\n\n"
        f"<b>Канал:</b> {channel}\n"
        f"<b>Время рассылки:</b> {schedule} UTC\n"
        f"<b>Автоматическая рассылка:</b> {status}"
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    if not message.from_user:
        return

    async with async_session_maker() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(message.from_user.id)

    if not user:
        await message.answer("Ты ещё не зарегистрирован. Нажми /start для начала.")
        return

    await message.answer(
        _format_settings(user),
        reply_markup=get_settings_keyboard(user.is_active),
    )


@router.callback_query(F.data == "toggle_active")
async def toggle_active(callback: CallbackQuery) -> None:
    if not callback.from_user or not callback.message:
        return

    async with async_session_maker() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(callback.from_user.id)

        if user:
            new_status = not user.is_active
            await repo.set_active(callback.from_user.id, new_status)
            user = await repo.get_by_id(callback.from_user.id)

    if user:
        await callback.message.edit_text(
            _format_settings(user),
            reply_markup=get_settings_keyboard(user.is_active),
        )

    await callback.answer()


@router.callback_query(F.data == "change_time")
async def change_time(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.message:
        return

    await callback.message.edit_text(
        "Выбери время для ежедневного дайджеста (UTC):",
        reply_markup=get_time_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_time:"))
async def set_time(callback: CallbackQuery) -> None:
    if not callback.from_user or not callback.message or not callback.data:
        return

    time_str = callback.data.split(":")[1]
    hour = int(time_str)

    async with async_session_maker() as session:
        repo = UserRepository(session)
        await repo.update_schedule(callback.from_user.id, hour, 0)
        user = await repo.get_by_id(callback.from_user.id)

    if user:
        await callback.message.edit_text(
            _format_settings(user),
            reply_markup=get_settings_keyboard(user.is_active),
        )

    await callback.answer(f"Время установлено: {hour:02d}:00 UTC")


@router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: CallbackQuery) -> None:
    if not callback.from_user or not callback.message:
        return

    async with async_session_maker() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(callback.from_user.id)

    if user:
        await callback.message.edit_text(
            _format_settings(user),
            reply_markup=get_settings_keyboard(user.is_active),
        )

    await callback.answer()
