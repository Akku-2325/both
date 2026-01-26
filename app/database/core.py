import aiosqlite
from app.config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;") 
        await db.execute("PRAGMA foreign_keys = ON")

        # 1. Сотрудники
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                pin_hash TEXT NOT NULL,
                balance INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Смены
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                report TEXT, 
                FOREIGN KEY (user_id) REFERENCES users(tg_id) ON DELETE RESTRICT
            )
        """)

        # 3. Сессии (кто залогинен)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                user_id INTEGER PRIMARY KEY,
                role TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(tg_id) ON DELETE CASCADE
            )
        """)
        
        # 4. Задачи
        await db.execute("""
            CREATE TABLE IF NOT EXISTS extra_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                reward INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                deadline TIMESTAMP,
                assigned_to INTEGER,
                message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Миграция для старых баз (на случай если таблица уже есть)
        try:
            await db.execute("ALTER TABLE extra_tasks ADD COLUMN message_id INTEGER")
        except:
            pass
        
        await db.commit()