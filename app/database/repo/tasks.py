import aiosqlite
from typing import List, Dict, Optional
from app.core.config import DB_PATH

async def create_personal_task_with_deadline(text: str, reward: int, deadline: str, tg_id: int, restaurant_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO extra_tasks (restaurant_id, text, reward, deadline, assigned_to, status) 
               VALUES (?, ?, ?, ?, ?, 'pending')""", 
            (restaurant_id, text, reward, deadline, tg_id)
        )
        await db.commit()
        return cursor.lastrowid

async def set_task_message_id(task_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE extra_tasks SET message_id = ? WHERE id = ?", (message_id, task_id))
        await db.commit()

async def mark_task_completed(task_id: int, restaurant_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE extra_tasks SET status = 'completed' WHERE id = ? AND restaurant_id = ?", 
            (task_id, restaurant_id)
        )
        await db.commit()

async def get_task_details(task_id: int, restaurant_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM extra_tasks WHERE id = ? AND restaurant_id = ?", 
            (task_id, restaurant_id)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def get_tasks_history(restaurant_id: int, limit: int = 10) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT t.id, t.text, t.reward, t.status, u.full_name 
            FROM extra_tasks t
            LEFT JOIN users u ON t.assigned_to = u.tg_id AND t.restaurant_id = u.restaurant_id
            WHERE t.restaurant_id = ?
            ORDER BY t.id DESC LIMIT ?
        """, (restaurant_id, limit)) as cur:
            return [dict(row) for row in await cur.fetchall()]

async def add_bonus(tg_id: int, restaurant_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = COALESCE(balance, 0) + ? WHERE tg_id = ? AND restaurant_id = ?", 
            (amount, tg_id, restaurant_id)
        )
        await db.commit()

async def get_balance(tg_id: int, restaurant_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT balance FROM users WHERE tg_id = ? AND restaurant_id = ?", 
            (tg_id, restaurant_id)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0
        
async def get_pending_tasks_details(restaurant_id: int) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT t.id, t.text, t.assigned_to, t.message_id, u.full_name 
            FROM extra_tasks t
            JOIN users u ON t.assigned_to = u.tg_id AND t.restaurant_id = u.restaurant_id
            WHERE t.status = 'pending' AND t.restaurant_id = ?
            ORDER BY t.id DESC
        """, (restaurant_id,)) as cur:
            return [dict(row) for row in await cur.fetchall()]

async def cancel_task_in_db(task_id: int, restaurant_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE extra_tasks SET status = 'canceled' WHERE id = ? AND restaurant_id = ?", 
            (task_id, restaurant_id)
        )
        await db.commit()

async def reset_balance(tg_id: int, restaurant_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = 0 WHERE tg_id = ? AND restaurant_id = ?", 
            (tg_id, restaurant_id)
        )
        await db.commit()