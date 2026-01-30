import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import BOT_TOKEN
from app.database.core import init_db
from app.middlewares.saas import SaasMiddleware

from app.handlers.super_admin import menu as super_admin_menu
from app.handlers import registration, auth, shifts, admin
from app.core.scheduler import send_hourly_reminders, clean_expired_tasks

logging.basicConfig(level=logging.INFO)

async def main():
    await init_db()
    
    session = AiohttpSession(proxy=None)
    bot = Bot(
        token=BOT_TOKEN, 
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    
    dp.message.outer_middleware(SaasMiddleware())
    dp.callback_query.outer_middleware(SaasMiddleware())

    dp.include_routers(
        super_admin_menu.router,
        registration.router,     
        auth.router,            
        shifts.router, 
        admin.router 
    )

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_hourly_reminders, 'interval', minutes=1, kwargs={'bot': bot})
    scheduler.add_job(clean_expired_tasks, 'interval', minutes=1, kwargs={'bot': bot})
    scheduler.start()

    print("✅ SaaS Бот запущен!")
    await dp.start_polling(bot, polling_timeout=60, allowed_updates=[])

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")