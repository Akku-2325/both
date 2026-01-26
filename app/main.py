import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties 
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import BOT_TOKEN
from app.database.core import init_db
from app.handlers import auth, shifts, admin, extras
from app.scheduler import send_hourly_reminders, clean_expired_tasks

logging.basicConfig(level=logging.INFO)

async def main():
    await init_db()
    
    bot = Bot(
        token=BOT_TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    dp.include_router(auth.router)
    dp.include_router(shifts.router)
    dp.include_router(admin.router)
    dp.include_router(extras.router)
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_hourly_reminders, 'interval', hours=1, kwargs={'bot': bot})
    scheduler.add_job(clean_expired_tasks, 'interval', minutes=1, kwargs={'bot': bot})
    scheduler.start()
    
    print("✅ Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")