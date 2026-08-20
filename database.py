import aiosqlite
from datetime import datetime
from typing import Optional

from config import DB_PATH


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                geo TEXT,
                has_experience INTEGER NOT NULL DEFAULT 1,
                experience_text TEXT,
                time_dedication TEXT,
                cs2_prime TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                admin_notify_message_id INTEGER,
                created_at TEXT NOT NULL
            )
            """
        )
        await db.commit()


async def create_application(
    user_id: int,
    username: Optional[str],
    first_name: Optional[str],
    geo: str,
    has_experience: bool,
    experience_text: Optional[str] = None,
    time_dedication: Optional[str] = None,
    cs2_prime: Optional[str] = None,
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO applications (
                user_id, username, first_name, geo, has_experience,
                experience_text, time_dedication, cs2_prime, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                first_name,
                geo,
                int(has_experience),
                experience_text,
                time_dedication,
                cs2_prime,
                datetime.utcnow().isoformat(),
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def set_admin_notify_message(app_id: int, message_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE applications SET admin_notify_message_id = ? WHERE id = ?",
            (message_id, app_id),
        )
        await db.commit()


async def get_application(app_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM applications WHERE id = ?", (app_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_applications_by_status(status: str, limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM applications
            WHERE status = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (status, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def update_status(app_id: int, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE applications SET status = ? WHERE id = ?",
            (status, app_id),
        )
        await db.commit()


async def count_by_status() -> dict[str, int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT status, COUNT(*) as cnt FROM applications GROUP BY status"
        )
        rows = await cursor.fetchall()
        return {row[0]: row[1] for row in rows}
