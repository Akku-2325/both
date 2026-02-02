import aiosqlite
import uuid
from typing import List, Dict
from app.core.config import DB_PATH

async def get_checklist(restaurant_id: int, role: str, shift_type: str) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if shift_type == 'full':
            types = ('morning', 'common', 'evening')
        elif shift_type == 'morning':
            types = ('morning', 'common')
        elif shift_type == 'evening':
            types = ('common', 'evening')
        else:
            types = ('common',)

        placeholders = ','.join(['?'] * len(types))
        
        query = f"""
            SELECT id, text, item_type FROM checklist_items 
            WHERE restaurant_id = ? AND role = ? AND shift_type IN ({placeholders})
            ORDER BY CASE shift_type 
                WHEN 'morning' THEN 1 
                WHEN 'common' THEN 2 
                WHEN 'evening' THEN 3 
            END, id ASC
        """
        params = (restaurant_id, role, *types)

        async with db.execute(query, params) as cur:
            rows = await cur.fetchall()
            return [dict(row) for row in rows]

async def add_checklist_item(restaurant_id: int, role: str, shift_type: str, text: str, item_type: str = 'simple'):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO checklist_items (restaurant_id, role, shift_type, text, item_type) VALUES (?, ?, ?, ?, ?)", 
            (restaurant_id, role, shift_type, text, item_type)
        )
        await db.commit()

async def is_checklist_item_exists(restaurant_id: int, role: str, shift_type: str, text: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM checklist_items WHERE restaurant_id = ? AND role = ? AND shift_type = ? AND text = ?", 
            (restaurant_id, role, shift_type, text)
        ) as cur:
            return await cur.fetchone() is not None

async def delete_checklist_item(item_id: int, restaurant_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM checklist_items WHERE id = ? AND restaurant_id = ?", 
            (item_id, restaurant_id)
        )
        await db.commit()

async def get_items_by_type(restaurant_id: int, role: str, shift_type: str) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM checklist_items 
            WHERE restaurant_id = ? AND role = ? AND shift_type = ?
            ORDER BY id ASC
        """, (restaurant_id, role, shift_type)) as cur:
            return [dict(row) for row in await cur.fetchall()]

async def add_reminder(restaurant_id: int, role: str, text: str, interval: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reminders (restaurant_id, role, text, interval_hours) VALUES (?, ?, ?, ?)",
            (restaurant_id, role, text, interval)
        )
        await db.commit()

async def delete_reminder(rem_id: int, restaurant_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM reminders WHERE id = ? AND restaurant_id = ?", 
            (rem_id, restaurant_id)
        )
        await db.commit()
        
async def get_all_reminders(restaurant_id: int) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM reminders WHERE restaurant_id = ?", (restaurant_id,)) as cur:
            return [dict(row) for row in await cur.fetchall()]

async def create_invite(restaurant_id: int, role: str) -> str:
    code = str(uuid.uuid4())[:8]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO invites (code, restaurant_id, role) VALUES (?, ?, ?)", 
            (code, restaurant_id, role)
        )
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