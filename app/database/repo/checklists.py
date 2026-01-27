import aiosqlite
import uuid
from typing import List, Dict
from app.config import DB_PATH

# --- ЧЕК-ЛИСТЫ ---
async def get_checklist(role: str, shift_type: str) -> List[str]:
    """Собирает чек-лист: задачи смены + общие задачи (common)"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Берем задачи конкретного типа (morning/evening) ИЛИ общие (common) для этой роли
        async with db.execute("""
            SELECT text FROM checklist_items 
            WHERE role = ? AND (shift_type = ? OR shift_type = 'common')
        """, (role, shift_type)) as cur:
            rows = await cur.fetchall()
            # Убираем дубликаты
            return list(dict.fromkeys([r[0] for r in rows]))

async def add_checklist_item(role: str, shift_type: str, text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO checklist_items (role, shift_type, text) VALUES (?, ?, ?)", 
            (role, shift_type, text)
        )
        await db.commit()

async def delete_checklist_item(item_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM checklist_items WHERE id = ?", (item_id,))
        await db.commit()

async def get_all_checklist_items(role: str) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM checklist_items WHERE role = ?", (role,)) as cur:
            return [dict(row) for row in await cur.fetchall()]

# --- НАПОМИНАНИЯ ---
async def add_reminder(role: str, text: str, interval: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reminders (role, text, interval_hours) VALUES (?, ?, ?)",
            (role, text, interval)
        )
        await db.commit()

async def get_reminders_for_scheduler() -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM reminders") as cur:
            return [dict(row) for row in await cur.fetchall()]

async def delete_reminder(rem_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM reminders WHERE id = ?", (rem_id,))
        await db.commit()
        
async def get_all_reminders() -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM reminders") as cur:
            return [dict(row) for row in await cur.fetchall()]

# --- ИНВАЙТЫ (ПРИГЛАШЕНИЯ) ---
async def create_invite(role: str) -> str:
    code = str(uuid.uuid4())[:8] # Короткий код
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO invites (code, role) VALUES (?, ?)", (code, role))
        await db.commit()
    return code

async def check_invite(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM invites WHERE code = ? AND is_used = 0", (code,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def mark_invite_used(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE invites SET is_used = 1 WHERE code = ?", (code,))
        await db.commit()