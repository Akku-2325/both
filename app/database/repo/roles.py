import aiosqlite
from typing import List, Dict
from app.config import DB_PATH

async def get_all_roles() -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM roles") as cur:
            return [dict(row) for row in await cur.fetchall()]

async def add_role(slug: str, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO roles (slug, name) VALUES (?, ?)", (slug, name))
        await db.commit()

async def delete_role(slug: str):
    if slug == 'admin': return # Защита от дурака
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM roles WHERE slug = ?", (slug,))
        await db.commit()