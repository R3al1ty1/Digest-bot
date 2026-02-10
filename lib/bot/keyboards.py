from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_settings_keyboard(is_active: bool) -> InlineKeyboardMarkup:
    toggle_text = "Выключить рассылку" if is_active else "Включить рассылку"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=toggle_text,
                    callback_data="toggle_active",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Изменить время",
                    callback_data="change_time",
                ),
            ],
        ]
    )


def get_time_keyboard() -> InlineKeyboardMarkup:
    # Generate time buttons for common hours
    hours = [6, 7, 8, 9, 10, 11, 12, 18, 19, 20, 21]

    buttons = []
    row = []

    for hour in hours:
        row.append(
            InlineKeyboardButton(
                text=f"{hour:02d}:00",
                callback_data=f"set_time:{hour}",
            )
        )
        if len(row) == 4:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    # Add back button
    buttons.append([
        InlineKeyboardButton(
            text="« Назад",
            callback_data="back_to_settings",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
