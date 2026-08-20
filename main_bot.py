import logging

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message

import database as db
from formatters import format_application, geo_display
from keyboards import (
    manual_keyboard,
    no_exp_intro_keyboard,
    step1_keyboard,
    step2_keyboard,
)
from states import FormState, get_session, reset_session
from texts import (
    APPLICATION_SENT,
    CS2_TEXT,
    NO_EXP_INTRO_TEXT,
    STEP1_TEXT,
    STEP2_TEXT,
    TIME_TEXT,
    manual_text,
    step3a_text,
)

logger = logging.getLogger(__name__)
router = Router()

NO_PREVIEW = LinkPreviewOptions(is_disabled=True)


async def edit_form(
    bot: Bot,
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup=None,
) -> None:
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
        link_preview_options=NO_PREVIEW,
    )


async def ask_text(message: Message, text: str) -> None:
    await message.answer(
        text,
        parse_mode=ParseMode.MARKDOWN,
        link_preview_options=NO_PREVIEW,
    )


async def notify_admins(admin_bot: Bot, app_id: int, admin_id: int | None = None) -> None:
    from admin_bot import get_admin_ids
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    app = await db.get_application(app_id)
    if not app:
        return

    admin_ids = get_admin_ids()
    if admin_id:
        admin_ids.add(admin_id)
    if not admin_ids:
        logger.warning(
            "No admin registered yet — send /start to the admin bot to receive notifications"
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить", callback_data=f"approve:{app_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить", callback_data=f"reject:{app_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💬 Написать пользователю",
                    callback_data=f"reply:{app_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📋 Открыть заявку",
                    callback_data=f"view:{app_id}",
                ),
            ],
        ]
    )

    text = format_application(app)
    for target_admin_id in admin_ids:
        try:
            msg = await admin_bot.send_message(
                target_admin_id,
                f"🔔 **Новая заявка!**\n\n{text}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
            )
            await db.set_admin_notify_message(app_id, msg.message_id)
        except Exception:
            logger.exception(
                "Failed to notify admin %s about application %s",
                target_admin_id,
                app_id,
            )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    reset_session(message.from_user.id)
    session = get_session(message.from_user.id)
    session.state = FormState.STEP1

    sent = await message.answer(
        STEP1_TEXT,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=step1_keyboard(),
        link_preview_options=NO_PREVIEW,
    )
    session.form_message_id = sent.message_id


@router.callback_query(F.data == "step1_next")
async def step1_next(callback: CallbackQuery) -> None:
    session = get_session(callback.from_user.id)
    session.state = FormState.STEP2

    await edit_form(
        callback.bot,
        callback.message.chat.id,
        callback.message.message_id,
        STEP2_TEXT,
        step2_keyboard(),
    )
    session.form_message_id = callback.message.message_id
    await callback.answer()


@router.callback_query(F.data.startswith("geo:"))
async def geo_selected(callback: CallbackQuery) -> None:
    geo_key = callback.data.split(":", 1)[1]
    session = get_session(callback.from_user.id)
    session.geo = geo_key
    session.form_message_id = callback.message.message_id

    if geo_key == "no_exp":
        session.has_experience = False
        session.state = FormState.NO_EXP_INTRO
        await edit_form(
            callback.bot,
            callback.message.chat.id,
            callback.message.message_id,
            NO_EXP_INTRO_TEXT,
            no_exp_intro_keyboard(),
        )
    else:
        session.has_experience = True
        session.state = FormState.EXPERIENCE
        label = geo_display(geo_key)
        await edit_form(
            callback.bot,
            callback.message.chat.id,
            callback.message.message_id,
            f"✅ **ГЕО: {label}**",
        )
        await callback.message.answer(
            step3a_text(label),
            parse_mode=ParseMode.MARKDOWN,
            link_preview_options=NO_PREVIEW,
        )

    await callback.answer()


@router.callback_query(F.data == "no_exp_next")
async def no_exp_next(callback: CallbackQuery) -> None:
    session = get_session(callback.from_user.id)
    session.state = FormState.MANUAL_CONFIRM
    session.manual_path = "no_exp"
    session.form_message_id = callback.message.message_id

    await edit_form(
        callback.bot,
        callback.message.chat.id,
        callback.message.message_id,
        manual_text(),
        manual_keyboard("no_exp"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("manual_ok:"))
async def manual_confirmed(callback: CallbackQuery) -> None:
    session = get_session(callback.from_user.id)
    session.state = FormState.TIME_DEDICATION

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        TIME_TEXT,
        parse_mode=ParseMode.MARKDOWN,
        link_preview_options=NO_PREVIEW,
    )
    await callback.answer()


@router.message(F.text)
async def handle_text(message: Message, admin_bot: Bot, admin_id: int | None) -> None:
    session = get_session(message.from_user.id)

    if session.state == FormState.IDLE:
        await message.answer("Жми /start, чтобы подать заявку.")
        return

    if session.state == FormState.EXPERIENCE:
        session.experience_text = message.text
        session.state = FormState.MANUAL_CONFIRM
        session.manual_path = "exp"
        await message.answer(
            manual_text(),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=manual_keyboard("exp"),
            link_preview_options=NO_PREVIEW,
        )
        return

    if session.state == FormState.TIME_DEDICATION:
        session.time_dedication = message.text
        session.state = FormState.CS2_PRIME
        await ask_text(message, CS2_TEXT)
        return

    if session.state == FormState.CS2_PRIME:
        session.cs2_prime = message.text
        await _submit_application(message, session, admin_bot, admin_id)
        return

    if session.state in (FormState.STEP1, FormState.STEP2, FormState.NO_EXP_INTRO):
        await message.answer("Жми кнопки в сообщении выше 👆")
        return

    if session.state == FormState.MANUAL_CONFIRM:
        await message.answer("Жми «✅ Я все понял» в сообщении выше 👆")
        return


async def _submit_application(
    message: Message,
    session,
    admin_bot: Bot,
    admin_id: int | None,
) -> None:
    geo_label = geo_display(session.geo) if session.geo else "—"

    app_id = await db.create_application(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        geo=geo_label,
        has_experience=session.has_experience,
        experience_text=session.experience_text,
        time_dedication=session.time_dedication,
        cs2_prime=session.cs2_prime,
    )

    await message.answer(
        APPLICATION_SENT,
        parse_mode=ParseMode.MARKDOWN,
        link_preview_options=NO_PREVIEW,
    )

    try:
        await notify_admins(admin_bot, app_id, admin_id)
    except Exception:
        logger.exception("Failed to notify admins about application %s", app_id)

    reset_session(message.from_user.id)
