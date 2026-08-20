import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import admin_bot
import database as db
import main_bot
from config import ADMIN_BOT_TOKEN, ADMIN_USERNAME, MAIN_BOT_TOKEN

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def resolve_admin_id(admin_bot_instance: Bot) -> int | None:
    try:
        chat = await admin_bot_instance.get_chat(f"@{ADMIN_USERNAME}")
        admin_bot.register_admin(chat.id)
        logger.info("Admin resolved: @%s (id=%s)", ADMIN_USERNAME, chat.id)
        return chat.id
    except Exception:
        logger.warning(
            "Could not resolve admin @%s by username. "
            "Send /start to admin bot after launch to register.",
            ADMIN_USERNAME,
        )
        return None


class AdminContext:
    admin_id: int | None = None


async def main() -> None:
    if not MAIN_BOT_TOKEN or not ADMIN_BOT_TOKEN:
        raise SystemExit(
            "Укажите MAIN_BOT_TOKEN и ADMIN_BOT_TOKEN в файле .env\n"
            "Скопируйте .env.example → .env и заполните токены."
        )

    await db.init_db()

    main_bot_instance = Bot(
        token=MAIN_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    admin_bot_instance = Bot(
        token=ADMIN_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    ctx = AdminContext()
    ctx.admin_id = await resolve_admin_id(admin_bot_instance)

    main_dp = Dispatcher()
    main_dp.include_router(main_bot.router)

    admin_dp = Dispatcher(storage=MemoryStorage())
    admin_dp.include_router(admin_bot.router)

    @admin_dp.update.outer_middleware()
    async def inject_main_bot(handler, event, data):
        data["main_bot"] = main_bot_instance
        return await handler(event, data)

    @main_dp.update.outer_middleware()
    async def inject_admin_context(handler, event, data):
        data["admin_bot"] = admin_bot_instance
        data["admin_id"] = ctx.admin_id
        return await handler(event, data)

    @admin_dp.update.outer_middleware()
    async def register_admin_on_update(handler, event, data):
        user = getattr(event, "from_user", None) or getattr(
            getattr(event, "message", None), "from_user", None
        )
        if user and (user.username or "").lower() == ADMIN_USERNAME.lower():
            admin_bot.register_admin(user.id)
            ctx.admin_id = user.id
        return await handler(event, data)

    logger.info("Starting bots...")
    await asyncio.gather(
        main_dp.start_polling(main_bot_instance),
        admin_dp.start_polling(admin_bot_instance),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped.")
