import aiosqlite
import hashlib
from datetime import datetime
from typing import Optional, List, Dict
from app.core.config import DB_PATH, TZ

def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()

async def add_user(tg_id: int, restaurant_id: int, full_name: str, role: str, pin: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (tg_id, restaurant_id, full_name, role, pin_hash, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(tg_id, restaurant_id) DO UPDATE SET 
                full_name=excluded.full_name, role=excluded.role, pin_hash=excluded.pin_hash, is_active=1
        """, (tg_id, restaurant_id, full_name, role, hash_pin(pin)))
        await db.commit()

async def get_user(tg_id: int, restaurant_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE tg_id = ? AND restaurant_id = ?", 
            (tg_id, restaurant_id)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def get_user_restaurants(tg_id: int) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT r.id, r.title, u.role 
            FROM users u
            JOIN restaurants r ON u.restaurant_id = r.id
            WHERE u.tg_id = ? AND u.is_active = 1 AND r.is_active = 1
        """, (tg_id,)) as cur:
            return [dict(row) for row in await cur.fetchall()]

async def get_all_users(restaurant_id: int) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE restaurant_id = ? ORDER BY role", 
            (restaurant_id,)
        ) as cur:
            return [dict(row) for row in await cur.fetchall()]

async def delete_user(tg_id: int, restaurant_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_active=0 WHERE tg_id=? AND restaurant_id=?", 
            (tg_id, restaurant_id)
        )
        await db.commit()

async def get_admins_ids(restaurant_id: int) -> List[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT tg_id FROM users WHERE role = 'admin' AND restaurant_id = ?", 
            (restaurant_id,)
        ) as cur:
            return [row[0] for row in await cur.fetchall()]

async def create_session(tg_id: int, restaurant_id: int, role: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO sessions (user_id, active_restaurant_id, role) VALUES (?, ?, ?)", 
            (tg_id, restaurant_id, role)
        )
        await db.commit()

async def get_session_info(tg_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT active_restaurant_id, role FROM sessions WHERE user_id = ?", (tg_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def delete_session(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM sessions WHERE user_id = ?", (tg_id,))
        await db.commit()

async def reset_user_kpi_date(tg_id: int, restaurant_id: int):
    now_str = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET kpi_reset_at = ? WHERE tg_id = ? AND restaurant_id = ?", 
            (now_str, tg_id, restaurant_id)
        )
        await db.commit()

async def fully_delete_user(tg_id: int, restaurant_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM sessions WHERE user_id = ? AND active_restaurant_id = ?", (tg_id, restaurant_id))
        await db.execute("DELETE FROM extra_tasks WHERE assigned_to = ? AND restaurant_id = ?", (tg_id, restaurant_id))
        await db.execute("DELETE FROM shifts WHERE user_id = ? AND restaurant_id = ?", (tg_id, restaurant_id))
        await db.execute("DELETE FROM users WHERE tg_id = ? AND restaurant_id = ?", (tg_id, restaurant_id))
        await db.commit()

async def get_session_role(tg_id: int) -> Optional[str]:
    info = await get_session_info(tg_id)
    return info['role'] if info else None