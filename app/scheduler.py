import aiosqlite
from datetime import datetime
from aiogram import Bot
from app.config import DB_PATH, TZ
from app.database.repo import shifts as shift_repo
from app.database.repo import checklists as check_repo

async def send_hourly_reminders(bot: Bot):
    shifts = await shift_repo.get_all_active_shifts_data()
    if not shifts: return
    
    reminders = await check_repo.get_reminders_for_scheduler()

    for shift in shifts:
        tg_id = shift['user_id']
        role = shift['role']
        
        try:
            start_time = datetime.strptime(shift['started_at'], "%Y-%m-%d %H:%M:%S")
            if start_time.tzinfo is None:
                start_time = TZ.localize(start_time)
            
            duration = datetime.now(TZ) - start_time
            hours_working = int(duration.total_seconds() // 3600)
            
            for r in reminders:
                if r['role'] == role and r['interval_hours'] == hours_working:
                     await bot.send_message(tg_id, f"🔔 <b>НАПОМИНАНИЕ:</b>\n\n{r['text']}")
        except Exception: 
            pass

async def clean_expired_tasks(bot: Bot):
    now_str = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT t.id, t.text, t.reward, u.full_name, t.assigned_to, t.message_id
            FROM extra_tasks t
            JOIN users u ON t.assigned_to = u.tg_id
            WHERE t.deadline IS NOT NULL 
            AND t.deadline < ? 
            AND t.status = 'pending'
        """, (now_str,)) as cur:
            expired_tasks = await cur.fetchall()

        if expired_tasks:
            await db.execute("""
                UPDATE extra_tasks SET status = 'expired'
                WHERE deadline IS NOT NULL AND deadline < ? AND status = 'pending'
            """, (now_str,))
            await db.commit()

            async with db.execute("SELECT tg_id FROM users WHERE role = 'admin'") as cur:
                admins = [row[0] for row in await cur.fetchall()]

            for task in expired_tasks:
                task_id, text, reward, user_name, user_id, message_id = task
                
                if message_id:
                    try:
                        new_text = (
                            f"🚫 <b>ВРЕМЯ ИСТЕКЛО!</b>\n"
                            f"📝 {text}\n"
                            f"❌ <i>Вы не успели выполнить задачу в срок.</i>"
                        )
                        await bot.edit_message_text(
                            text=new_text,
                            chat_id=user_id,
                            message_id=message_id,
                            reply_markup=None
                        )
                    except Exception:
                        pass
                
                admin_msg = (
                    f"❌ <b>ПРОСРОЧЕНО (Авто)</b>\n"
                    f"👤 <b>Кто:</b> {user_name}\n"
                    f"📝 <b>Задача:</b> {text}\n"
                    f"💰 <b>Потеряно:</b> {reward} баллов"
                )
                for admin_id in admins:
                    try: await bot.send_message(admin_id, admin_msg)
                    except: pass