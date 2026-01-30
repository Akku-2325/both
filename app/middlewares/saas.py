import aiosqlite
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from app.core.config import DB_PATH

class SaasMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT s.active_restaurant_id, s.role, r.is_active 
                FROM sessions s
                LEFT JOIN restaurants r ON s.active_restaurant_id = r.id
                WHERE s.user_id = ?
            """, (user_id,)) as cur:
                row = await cur.fetchone()
                
                if row:
                    is_root_cmd = False
                    if isinstance(event, Message) and event.text:
                        if event.text.startswith("/root_login") or event.text == "🚪 Выйти":
                            is_root_cmd = True

                    if row["active_restaurant_id"] and not row["is_active"] and not is_root_cmd:
                        try:
                            if isinstance(event, Message):
                                await event.answer("❄️ <b>Ваша кофейня временно заморожена.</b>\nОбратитесь к владельцу платформы.")
                            elif isinstance(event, CallbackQuery):
                                await event.answer("❄️ Доступ ограничен.", show_alert=True)
                        except: pass
                        return

                    data["restaurant_id"] = row["active_restaurant_id"]
                    data["role"] = row["role"]
                else:
                    data["restaurant_id"] = None
                    data["role"] = None

        return await handler(event, data)