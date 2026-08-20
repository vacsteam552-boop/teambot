import logging

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import database as db
from config import ADMIN_USERNAME, DISCORD_INVITE
from formatters import format_application
from texts import APPROVED_TEXT, REJECTED_TEXT

logger = logging.getLogger(__name__)
router = Router()

_admin_ids: set[int] = set()


class AdminReply(StatesGroup):
    waiting_message = State()


def is_admin(user) -> bool:
    if not user:
        return False
    if user.id in _admin_ids:
        return True
    username = (user.username or "").lower()
    return username == ADMIN_USERNAME.lower()


def register_admin(user_id: int) -> None:
    _admin_ids.add(user_id)


def get_admin_ids() -> set[int]:
    return set(_admin_ids)


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏳ Новые заявки", callback_data="list:pending"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✅ Одобренные", callback_data="list:approved"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонённые", callback_data="list:rejected"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📊 Статистика", callback_data="stats"
                ),
            ],
        ]
    )


def application_actions_keyboard(app_id: int, status: str) -> InlineKeyboardMarkup:
    rows = []

    if status == "pending":
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Одобрить", callback_data=f"approve:{app_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить", callback_data=f"reject:{app_id}"
                ),
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="💬 Написать пользователю",
                callback_data=f"reply:{app_id}",
            ),
        ]
    )
    rows.append(
        [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def deny_if_not_admin(message: Message) -> bool:
    if not is_admin(message.from_user):
        await message.answer("⛔ Доступ только для администратора.")
        return False
    return True


@router.message(CommandStart())
async def admin_start(message: Message) -> None:
    if not is_admin(message.from_user):
        await message.answer(
            "⛔ Этот бот доступен только администратору.\n"
            f"Ваш username: @{message.from_user.username or 'нет'}"
        )
        return

    register_admin(message.from_user.id)
    await message.answer(
        "🛠 **Панель администратора**\n\n"
        "Здесь вы можете просматривать заявки, одобрять или отклонять их, "
        "а также писать пользователям от лица основного бота.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_panel_keyboard(),
    )


@router.message(Command("admin"))
async def admin_command(message: Message) -> None:
    await admin_start(message)


@router.callback_query(F.data == "menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "🛠 **Панель администратора**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_panel_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "stats")
async def show_stats(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    counts = await db.count_by_status()
    pending = counts.get("pending", 0)
    approved = counts.get("approved", 0)
    rejected = counts.get("rejected", 0)
    total = pending + approved + rejected

    text = (
        "📊 **Статистика заявок**\n\n"
        f"⏳ Ожидают: {pending}\n"
        f"✅ Одобрено: {approved}\n"
        f"❌ Отклонено: {rejected}\n"
        f"📋 Всего: {total}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
        ]
    )

    await callback.message.edit_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("list:"))
async def list_applications(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    status = callback.data.split(":", 1)[1]
    apps = await db.get_applications_by_status(status)

    status_titles = {
        "pending": "⏳ Новые заявки",
        "approved": "✅ Одобренные",
        "rejected": "❌ Отклонённые",
    }

    if not apps:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
            ]
        )
        await callback.message.edit_text(
            f"{status_titles.get(status, 'Заявки')}\n\nЗаявок нет.",
            reply_markup=keyboard,
        )
        await callback.answer()
        return

    buttons = []
    for app in apps[:15]:
        username = app.get("username")
        label = f"#{app['id']} @{username}" if username else f"#{app['id']}"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=label, callback_data=f"view:{app['id']}"
                )
            ]
        )

    buttons.append(
        [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
    )

    await callback.message.edit_text(
        f"{status_titles.get(status, 'Заявки')}\n\nВыберите заявку:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("view:"))
async def view_application(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    app_id = int(callback.data.split(":", 1)[1])
    app = await db.get_application(app_id)

    if not app:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    await callback.message.edit_text(
        format_application(app),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=application_actions_keyboard(app_id, app["status"]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("approve:"))
async def approve_application(
    callback: CallbackQuery, main_bot: Bot
) -> None:
    if not is_admin(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    app_id = int(callback.data.split(":", 1)[1])
    app = await db.get_application(app_id)

    if not app:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    if app["status"] != "pending":
        await callback.answer("Заявка уже обработана", show_alert=True)
        return

    await db.update_status(app_id, "approved")

    try:
        await main_bot.send_message(
            app["user_id"],
            APPROVED_TEXT,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        logger.exception("Failed to notify user %s about approval", app["user_id"])

    app = await db.get_application(app_id)
    await callback.message.edit_text(
        format_application(app),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=application_actions_keyboard(app_id, "approved"),
    )
    await callback.answer("Заявка одобрена ✅")


@router.callback_query(F.data.startswith("reject:"))
async def reject_application(callback: CallbackQuery, main_bot: Bot) -> None:
    if not is_admin(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    app_id = int(callback.data.split(":", 1)[1])
    app = await db.get_application(app_id)

    if not app:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    if app["status"] != "pending":
        await callback.answer("Заявка уже обработана", show_alert=True)
        return

    await db.update_status(app_id, "rejected")

    try:
        await main_bot.send_message(
            app["user_id"],
            REJECTED_TEXT,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        logger.exception("Failed to notify user %s about rejection", app["user_id"])

    app = await db.get_application(app_id)
    await callback.message.edit_text(
        format_application(app),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=application_actions_keyboard(app_id, "rejected"),
    )
    await callback.answer("Заявка отклонена ❌")


@router.callback_query(F.data.startswith("reply:"))
async def start_reply(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    app_id = int(callback.data.split(":", 1)[1])
    app = await db.get_application(app_id)

    if not app:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    await state.set_state(AdminReply.waiting_message)
    await state.update_data(reply_app_id=app_id)

    username = app.get("username")
    user_label = f"@{username}" if username else str(app["user_id"])

    await callback.message.answer(
        f"✍️ Напишите сообщение для {user_label}.\n"
        "Оно будет отправлено от лица основного бота.\n\n"
        "Отправьте /cancel для отмены."
    )
    await callback.answer()


@router.message(Command("cancel"))
async def cancel_reply(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user):
        return

    current = await state.get_state()
    if current == AdminReply.waiting_message:
        await state.clear()
        await message.answer(
            "Отменено.",
            reply_markup=admin_panel_keyboard(),
        )


@router.message(AdminReply.waiting_message)
async def send_reply_to_user(
    message: Message, state: FSMContext, main_bot: Bot
) -> None:
    if not is_admin(message.from_user):
        return

    data = await state.get_data()
    app_id = data.get("reply_app_id")
    app = await db.get_application(app_id)

    if not app:
        await message.answer("Заявка не найдена.")
        await state.clear()
        return

    try:
        await main_bot.send_message(app["user_id"], message.text)
    except Exception as exc:
        logger.exception("Failed to send message to user %s", app["user_id"])
        await message.answer(f"❌ Не удалось отправить: {exc}")
        return

    await state.clear()
    await message.answer(
        f"✅ Сообщение отправлено пользователю (заявка #{app_id}).",
        reply_markup=admin_panel_keyboard(),
    )
