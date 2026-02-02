import json
import aiosqlite
from datetime import datetime
from app.database.repo import shifts as shift_repo, tasks as task_repo, roles as role_repo
from app.core.config import DB_PATH, TZ

def calculate_duration(start_str: str):
    start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.now(TZ).replace(tzinfo=None)
    duration = end_dt - start_dt
    hours = int(duration.total_seconds() // 3600)
    minutes = int((duration.total_seconds() % 3600) // 60)
    return hours, minutes

async def toggle_duty(tg_id: int, restaurant_id: int, task_index: int, is_checked: bool, master_tasks_list: list):
    active = await shift_repo.get_active_shift(tg_id, restaurant_id)
    if not active: return None

    try: 
        data = json.loads(active['report']) if active['report'] else {}
    except json.JSONDecodeError:
        data = {}

    user_duties = data.get('duties', [])

    if len(user_duties) != len(master_tasks_list):
        new_duties = []
        for i, task_data in enumerate(master_tasks_list):
            title = task_data['text']
            is_done = False
            if i < len(user_duties):
                if user_duties[i].get('title') == title:
                    is_done = user_duties[i].get('done', False)
            
            new_duties.append({"title": title, "done": is_done})
        user_duties = new_duties

    if 0 <= task_index < len(user_duties):
        user_duties[task_index]['done'] = is_checked
        user_duties[task_index]['title'] = master_tasks_list[task_index]['text']

    data['duties'] = user_duties
    new_report = json.dumps(data)
    await shift_repo.update_shift_report(active['id'], restaurant_id, new_report)
    
    return [t['done'] for t in user_duties]

async def close_shift_logic(tg_id: int, restaurant_id: int, raw_data: str, user_name: str, tasks_list: list, comment: str = None):
    active_shift = await shift_repo.get_active_shift(tg_id, restaurant_id)
    if not active_shift: return None

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT text FROM extra_tasks WHERE assigned_to = ? AND status = 'pending' AND restaurant_id = ?", 
            (tg_id, restaurant_id)
        ) as cur:
            pending_tasks = await cur.fetchall()
        
        await db.execute(
            "UPDATE extra_tasks SET status = 'canceled' WHERE assigned_to = ? AND status = 'pending' AND restaurant_id = ?", 
            (tg_id, restaurant_id)
        )
        await db.commit()

    await shift_repo.end_shift(active_shift['id'], restaurant_id, raw_data)
    
    try:
        data = json.loads(raw_data)
    except:
        data = {}

    roles_map = await role_repo.get_roles_map(restaurant_id)
    r_name = roles_map.get(active_shift['role'], active_shift['role'])

    hours, minutes = calculate_duration(active_shift['started_at'])
    
    user_duties = data.get('duties', [])
    
    if not user_duties:
        user_duties = [{"title": t['text'], "done": False} for t in tasks_list]

    missed = []
    completed_count = 0
    
    for i, task_data in enumerate(tasks_list):
        title = task_data['text']
        is_done = False
        if i < len(user_duties):
            is_done = user_duties[i].get('done', False)
        
        if is_done:
            completed_count += 1
        else:
            missed.append(title)

    total = len(tasks_list)
    efficiency = int((completed_count / total) * 100) if total > 0 else 0
    
    if efficiency == 100: grade = "⭐⭐⭐ (Идеально)"
    elif efficiency >= 80: grade = "⭐⭐ (Хорошо)"
    else: grade = "⚠️ (Внимание!)"

    user_report = (
        f"🏁 <b>СМЕНА ЗАКРЫТА #{active_shift['id']}</b>\n"
        f"➖➖➖➖➖➖➖➖\n"
        f"👤 <b>Сотрудник:</b> {user_name} ({r_name})\n"
        f"🕒 <b>Длительность:</b> {hours}ч {minutes}мин\n"
        f"📈 <b>Эффективность:</b> {efficiency}% {grade}\n"
        f"➖➖➖➖➖➖➖➖\n"
    )
    
    if missed:
        user_report += "<b>❌ НЕ ВЫПОЛНЕНО (Чек-лист):</b>\n" + "\n".join(f"— {t}" for t in missed) + "\n\n"
    else:
        user_report += "✅ <i>Чек-лист выполнен полностью!</i>\n\n"

    if pending_tasks:
        user_report += "<b>🚫 ПРОПУЩЕННЫЕ ДОП. ЗАДАНИЯ:</b>\n" + "\n".join(f"— {t[0]}" for t in pending_tasks) + "\n\n"

    if comment:
        user_report += f"💬 <b>Комментарий:</b> {comment}\n"

    return {
        "user_report": user_report
    }