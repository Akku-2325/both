import aiosqlite
from app.config import DB_PATH

async def _seed_data(db):
    # 1. Базовые роли
    roles = [("admin", "Администратор"), ("barista", "Бариста"), ("cashier", "Кассир"), ("cook", "Повар")]
    await db.executemany("INSERT OR IGNORE INTO roles (slug, name) VALUES (?, ?)", roles)

    # 2. Базовые чек-листы (если пусто)
    async with db.execute("SELECT count(*) FROM checklist_items") as cur:
        count = await cur.fetchone()
        if count[0] == 0:
            tasks = [
                ("barista", "morning", "Включить кофемашину"),
                ("barista", "evening", "Помыть холдеры"),
                ("cashier", "morning", "Пересчитать кассу"),
                ("cashier", "evening", "Z-отчет"),
                ("cook", "morning", "Прогреть гриль"),
                ("cook", "evening", "Вынести мусор"),
            ]
            await db.executemany("INSERT INTO checklist_items (role, shift_type, text) VALUES (?, ?, ?)", tasks)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;") 
        await db.execute("PRAGMA foreign_keys = ON")

        # --- ТАБЛИЦА РОЛЕЙ (НОВОЕ) ---
        await db.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                slug TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                pin_hash TEXT NOT NULL,
                balance INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                kpi_reset_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                shift_type TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                report TEXT, 
                FOREIGN KEY (user_id) REFERENCES users(tg_id) ON DELETE RESTRICT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                user_id INTEGER PRIMARY KEY,
                role TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(tg_id) ON DELETE CASCADE
            )
        """)
        
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
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS checklist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                shift_type TEXT NOT NULL,
                text TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                interval_hours INTEGER NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS invites (
                code TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                is_used BOOLEAN DEFAULT 0
            )
        """)

        # Миграции
        try: await db.execute("ALTER TABLE extra_tasks ADD COLUMN message_id INTEGER")
        except: pass
        try: await db.execute("ALTER TABLE extra_tasks ADD COLUMN deadline TIMESTAMP")
        except: pass
        
        # Заполнение начальными данными
        await _seed_data(db)
        await db.commit()