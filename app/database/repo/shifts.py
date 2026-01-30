import aiosqlite
from datetime import datetime
from typing import Optional, Dict, List
from app.core.config import DB_PATH, TZ

def now():
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

async def start_shift(tg_id: int, restaurant_id: int, role: str, shift_type: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO shifts (user_id, restaurant_id, role, shift_type, started_at) VALUES (?, ?, ?, ?, ?)", 
            (tg_id, restaurant_id, role, shift_type, now())
        )
        await db.commit()

async def get_active_shift(tg_id: int, restaurant_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM shifts 
            WHERE user_id = ? AND restaurant_id = ? AND ended_at IS NULL 
            ORDER BY id DESC LIMIT 1
        """, (tg_id, restaurant_id)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def end_shift(shift_id: int, restaurant_id: int, report_json: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE shifts SET ended_at = ?, report = ? WHERE id = ? AND restaurant_id = ?", 
            (now(), report_json, shift_id, restaurant_id)
        )
        await db.commit()

async def update_shift_report(shift_id: int, restaurant_id: int, report_json: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE shifts SET report = ? WHERE id = ? AND restaurant_id = ?", 
            (report_json, shift_id, restaurant_id)
        )
        await db.commit()

async def get_last_shifts(tg_id: int, restaurant_id: int, limit: int = 5) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM shifts 
            WHERE user_id = ? AND restaurant_id = ? AND ended_at IS NOT NULL 
            ORDER BY id DESC LIMIT ?
        """, (tg_id, restaurant_id, limit)) as cur:
            return [dict(row) for row in await cur.fetchall()]

async def get_all_active_shifts_data(restaurant_id: int) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT s.*, u.full_name 
            FROM shifts s
            JOIN users u ON s.user_id = u.tg_id AND s.restaurant_id = u.restaurant_id
            WHERE s.ended_at IS NULL AND s.restaurant_id = ?
        """, (restaurant_id,)) as cur:
            return [dict(row) for row in await cur.fetchall()]

async def get_monthly_stats(tg_id: int, restaurant_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM shifts 
            WHERE user_id = ? 
            AND restaurant_id = ?
            AND ended_at IS NOT NULL
            AND started_at >= COALESCE(
                (SELECT kpi_reset_at FROM users WHERE tg_id = ? AND restaurant_id = ?), 
                date('now', '-30 days')
            )
        """, (tg_id, restaurant_id, tg_id, restaurant_id)) as cur:
            return [dict(row) for row in await cur.fetchall()]