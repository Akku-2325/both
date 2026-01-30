import aiosqlite
from typing import List, Dict, Optional
from app.core.config import DB_PATH

async def get_all_roles(restaurant_id: int) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM roles WHERE restaurant_id = ?", 
            (restaurant_id,)
        ) as cur:
            return [dict(row) for row in await cur.fetchall()]

async def get_role(restaurant_id: int, slug: str) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM roles WHERE restaurant_id = ? AND slug = ?", 
            (restaurant_id, slug)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def add_role(restaurant_id: int, slug: str, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO roles (slug, restaurant_id, name) VALUES (?, ?, ?)", 
            (slug, restaurant_id, name)
        )
        await db.commit()

async def update_role_name(restaurant_id: int, slug: str, new_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE roles SET name = ? WHERE restaurant_id = ? AND slug = ?", 
            (new_name, restaurant_id, slug)
        )
        await db.commit()

async def delete_role(restaurant_id: int, slug: str):
    if slug == 'admin': return 
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM roles WHERE restaurant_id = ? AND slug = ?", 
            (restaurant_id, slug)
        )
        await db.commit()

async def get_roles_map(restaurant_id: int) -> Dict[str, str]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT slug, name FROM roles WHERE restaurant_id = ?", 
            (restaurant_id,)
        ) as cur:
            rows = await cur.fetchall()
            return {row['slug']: row['name'] for row in rows}