import aiosqlite
from datetime import datetime
from aiogram import Bot
from app.config import DB_PATH, TZ
from app.database.repo import shifts as shift_repo

async def send_hourly_reminders(bot: Bot):
    shifts = await shift_repo.get_all_active_shifts_data()
    if not shifts: return

    text_template = (
        "⏳ Вы на смене уже <b>{hours} ч.</b>\n\n"
        "🔔 <b>Чек-поинт чистоты:</b>\n"
        "▫️ Протрите столы\n"
        "▫️ Проверьте салфетки\n"
        "▫️ Улыбнитесь! 🙂"
    )

    for shift in shifts:
        tg_id = shift['user_id']
        try:
            start_time = datetime.strptime(shift['started_at'], "%Y-%m-%d %H:%M:%S")
            if start_time.tzinfo is None:
                start_time = TZ.localize(start_time)
            duration = datetime.now(TZ) - start_time
            hours_working = int(duration.total_seconds() // 3600)
            await bot.send_message(tg_id, text_template.format(hours=hours_working))
        except: pass

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