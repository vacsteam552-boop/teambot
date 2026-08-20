from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def step1_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➡️", callback_data="step1_next")]
        ]
    )


def step2_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇨🇳 Китай", callback_data="geo:china"),
                InlineKeyboardButton(text="🇪🇺 Европа", callback_data="geo:europe"),
            ],
            [
                InlineKeyboardButton(text="🇺🇸 Америка", callback_data="geo:america"),
                InlineKeyboardButton(text="❓ Другое", callback_data="geo:other"),
            ],
            [
                InlineKeyboardButton(text="🚫 Без опыта", callback_data="geo:no_exp"),
            ],
        ]
    )


def no_exp_intro_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➡️", callback_data="no_exp_next")]
        ]
    )


def manual_keyboard(path: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Я все понял",
                    callback_data=f"manual_ok:{path}",
                )
            ]
        ]
    )
