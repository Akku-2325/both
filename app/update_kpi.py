import asyncio
import aiosqlite
from app.config import DB_PATH

async def update_db():
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            # Добавляем колонку для даты сброса статистики
            await db.execute("ALTER TABLE users ADD COLUMN kpi_reset_at TIMESTAMP")
            await db.commit()
            print("✅ Успешно! Колонка kpi_reset_at добавлена.")
        except Exception as e:
            print(f"⚠️ Ошибка (возможно, уже есть): {e}")

if __name__ == "__main__":
    asyncio.run(update_db())