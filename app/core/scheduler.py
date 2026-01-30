import aiosqlite
import asyncio
from datetime import datetime
from aiogram import Bot
from app.core.config import DB_PATH, TZ

async def send_hourly_reminders(bot: Bot):
    try:
        now = datetime.now(TZ).replace(tzinfo=None)
        
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            async with db.execute("""
                SELECT s.user_id, s.restaurant_id, s.role, s.started_at 
                FROM shifts s
                WHERE s.ended_at IS NULL
            """) as cur:
                active_shifts = [dict(row) for row in await cur.fetchall()]

            if not active_shifts: return

            async with db.execute("SELECT * FROM reminders") as cur:
                all_reminders = [dict(row) for row in await cur.fetchall()]

        if not all_reminders: return

        for shift in active_shifts:
            try:
                tg_id = shift['user_id']
                r_id = shift['restaurant_id']
                role_slug = shift['role']
                
                start_time = datetime.strptime(shift['started_at'], "%Y-%m-%d %H:%M:%S")
                diff_min = int((now - start_time).total_seconds() // 60)

                relevant_reminders = [
                    rem for rem in all_reminders 
                    if rem['restaurant_id'] == r_id and rem['role'] == role_slug
                ]

                for r in relevant_reminders:
                    interval = r['interval_hours']
                    if interval > 0 and diff_min > 0 and (diff_min % interval == 0):
                        try:
                            await bot.send_message(tg_id, f"🔔 <b>НАПОМИНАНИЕ:</b>\n\n{r['text']}")
                            await asyncio.sleep(0.1) 
                        except Exception as e:
                            print(f"Не удалось отправить (user {tg_id}): {e}")

            except Exception as e:
                print(f"Ошибка в цикле напоминаний: {e}")
                continue

    except Exception as e:
        print(f"Глобальная ошибка шедулера: {e}")

async def clean_expired_tasks(bot: Bot):
    try:
        now_str = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("""
                SELECT t.id, t.text, t.reward, t.assigned_to, t.message_id, t.restaurant_id, u.full_name
                FROM extra_tasks t
                JOIN users u ON t.assigned_to = u.tg_id AND t.restaurant_id = u.restaurant_id
                WHERE t.status = 'pending' AND t.deadline < ?
            """, (now_str,)) as cur:
                expired_tasks = await cur.fetchall()

            if not expired_tasks: return

            for task in expired_tasks:
                tid, text, reward, uid, mid, rid, name = task
                
                await db.execute("UPDATE extra_tasks SET status = 'expired' WHERE id = ?", (tid,))
                
                if mid:
                    try:
                        await bot.edit_message_text(
                            chat_id=uid,
                            message_id=mid,
                            text=f"🚫 <b>ВРЕМЯ ИСТЕКЛО!</b>\n📝 {text}\n❌ Задание провалено.",
                            reply_markup=None
                        )
                    except: pass
                
                async with db.execute("SELECT tg_id FROM users WHERE role = 'admin' AND restaurant_id = ?", (rid,)) as acur:
                    admins = [row[0] for row in await acur.fetchall()]

                admin_msg = f"❌ <b>ПРОСРОЧЕНО (Авто)</b>\n👤 Кто: {name}\n📝 Задача: {text}\n💰 Потеряно: {reward} баллов"
                
                for a_id in admins:
                    try: await bot.send_message(a_id, admin_msg)
                    except: pass
            
            await db.commit()

    except Exception as e:
        print(f"Ошибка в clean_expired_tasks: {e}")