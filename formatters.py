import re
from datetime import datetime

from texts import GEO_LABELS

_MD_SPECIAL = re.compile(r"([\\_*`\[])")


def escape_markdown(text: str | None) -> str:
    if not text:
        return ""
    return _MD_SPECIAL.sub(r"\\\1", text)


def format_user_link(username: str | None, user_id: int, first_name: str | None) -> str:
    if username:
        return f"@{escape_markdown(username)} ({user_id})"
    name = escape_markdown(first_name) or "Без имени"
    return f"{name} ({user_id})"


def format_application(app: dict) -> str:
    created = app.get("created_at", "")
    try:
        dt = datetime.fromisoformat(created)
        created_str = dt.strftime("%d.%m.%Y %H:%M UTC")
    except ValueError:
        created_str = created

    user_line = format_user_link(
        app.get("username"), app["user_id"], app.get("first_name")
    )
    geo = escape_markdown(app.get("geo")) or "—"
    has_exp = bool(app.get("has_experience"))

    lines = [
        f"📋 **Заявка #{app['id']}**",
        f"👤 Пользователь: {user_line}",
        f"📅 Дата: {created_str}",
        f"🌍 ГЕО: {geo}",
        f"💼 Опыт: {'Да' if has_exp else 'Нет'}",
    ]

    if has_exp and app.get("experience_text"):
        lines.append(f"\n📄 **Опыт:**\n{escape_markdown(app['experience_text'])}")

    if app.get("time_dedication"):
        lines.append(
            f"\n⏰ **Время на ворк:**\n{escape_markdown(app['time_dedication'])}"
        )

    if app.get("cs2_prime"):
        lines.append(f"\n🎮 **Prime CS2:**\n{escape_markdown(app['cs2_prime'])}")

    status_map = {
        "pending": "⏳ Ожидает",
        "approved": "✅ Одобрена",
        "rejected": "❌ Отклонена",
    }
    lines.append(f"\n📌 Статус: {status_map.get(app['status'], app['status'])}")

    return "\n".join(lines)


def geo_display(geo_key: str) -> str:
    return GEO_LABELS.get(geo_key, geo_key)
