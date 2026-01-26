import aiosqlite
from typing import List, Dict, Any, Optional
from app.config import DB_PATH

async def _get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db

async def execute(query: str, params: tuple = (), commit: bool = True) -> int:
    """Выполняет запрос INSERT/UPDATE/DELETE"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(query, params)
        if commit:
            await db.commit()
        return cursor.lastrowid

async def fetch_one(query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    """Возвращает одну строку в виде словаря"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def fetch_all(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Возвращает список строк в виде словарей"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]