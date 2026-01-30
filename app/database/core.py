import aiosqlite
from app.core.config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;") 
        await db.execute("PRAGMA foreign_keys = ON")
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS license_keys (
                key_code TEXT PRIMARY KEY,
                is_used BOOLEAN DEFAULT 0,
                target_username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                activated_by_tg_id INTEGER,
                activated_at TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS restaurants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                owner_tg_id INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT 1, 
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                slug TEXT,
                restaurant_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                PRIMARY KEY (slug, restaurant_id),
                FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER,
                restaurant_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                pin_hash TEXT NOT NULL,
                balance INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                kpi_reset_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (tg_id, restaurant_id),
                FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                user_id INTEGER PRIMARY KEY,
                active_restaurant_id INTEGER,
                role TEXT,
                FOREIGN KEY (active_restaurant_id) REFERENCES restaurants(id) ON DELETE SET NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                shift_type TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                report TEXT, 
                FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id, restaurant_id) REFERENCES users(tg_id, restaurant_id) ON DELETE RESTRICT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS extra_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                reward INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                deadline TIMESTAMP,
                assigned_to INTEGER,
                message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS checklist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                shift_type TEXT NOT NULL,
                text TEXT NOT NULL,
                FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                interval_hours INTEGER NOT NULL,
                FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS invites (
                code TEXT PRIMARY KEY,
                restaurant_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                is_used BOOLEAN DEFAULT 0,
                FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE
            )
        """)
        
        await db.commit()