import uuid
import aiosqlite
from typing import List, Dict, Optional
from app.core.config import DB_PATH

async def create_license_key(admin_id: int, target_username: Optional[str] = None) -> str:
    key = f"LICENSE-{uuid.uuid4().hex[:8].upper()}"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO license_keys (key_code, activated_by_tg_id, target_username) VALUES (?, ?, ?)",
            (key, admin_id, target_username)
        )
        await db.commit()
    return key

async def get_license_key(key_code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM license_keys WHERE key_code = ?", (key_code,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def register_new_restaurant(title: str, owner_tg_id: int, owner_username: Optional[str], owner_name: str, pin_hash: str, key_code: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM license_keys WHERE key_code = ?", (key_code,)) as cur:
            row = await cur.fetchone()
            if not row or row['is_used']: return False
            if row['target_username']:
                clean_target = row['target_username'].lstrip('@').lower()
                clean_owner = owner_username.lower() if owner_username else ""
                if clean_target != clean_owner: return False

        async with db.execute("INSERT INTO restaurants (title, owner_tg_id, is_active) VALUES (?, ?, 1)", (title, owner_tg_id)) as cursor:
            restaurant_id = cursor.lastrowid

        await db.execute("INSERT INTO roles (slug, restaurant_id, name) VALUES (?, ?, ?)", ("admin", restaurant_id, "Владелец"))
        await db.execute("INSERT INTO users (tg_id, restaurant_id, full_name, role, pin_hash, is_active) VALUES (?, ?, ?, ?, ?, 1)", (owner_tg_id, restaurant_id, owner_name, "admin", pin_hash))
        await db.execute("UPDATE license_keys SET is_used = 1, activated_at = CURRENT_TIMESTAMP WHERE key_code = ?", (key_code,))
        await db.execute("INSERT OR REPLACE INTO sessions (user_id, active_restaurant_id, role) VALUES (?, ?, ?)", (owner_tg_id, restaurant_id, "admin"))
        await db.commit()
        return True

async def delete_restaurant(restaurant_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM sessions WHERE active_restaurant_id = ?", (restaurant_id,))
        await db.execute("DELETE FROM restaurants WHERE id = ?", (restaurant_id,))
        await db.commit()

async def get_restaurant_info(restaurant_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM restaurants WHERE id = ?", (restaurant_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def get_restaurant_users(restaurant_id: int) -> List[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT tg_id FROM users WHERE restaurant_id = ?", (restaurant_id,)) as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]

async def get_platform_stats() -> Dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM restaurants") as c:
            cafes = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            users = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM shifts WHERE ended_at IS NULL") as c:
            shifts = (await c.fetchone())[0]
    return {"cafes": cafes, "users": users, "shifts": shifts}

async def get_all_restaurants() -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, title, is_active FROM restaurants ORDER BY id DESC") as cur:
            return [dict(row) for row in await cur.fetchall()]

async def toggle_restaurant_status(restaurant_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT is_active FROM restaurants WHERE id = ?", (restaurant_id,)) as cur:
            row = await cur.fetchone()
            if not row: return None
            status = row[0]
        
        new_status = 0 if status else 1
        await db.execute("UPDATE restaurants SET is_active = ? WHERE id = ?", (new_status, restaurant_id))
        
        if new_status == 0:
            await db.execute("DELETE FROM sessions WHERE active_restaurant_id = ?", (restaurant_id,))
            
        await db.commit()
        return new_status

async def is_restaurant_active(restaurant_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT is_active FROM restaurants WHERE id = ?", (restaurant_id,)) as cur:
            row = await cur.fetchone()
            return bool(row[0]) if row else False

async def get_all_owners_ids() -> List[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT DISTINCT owner_tg_id FROM restaurants") as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]