import json
import aiosqlite
from datetime import datetime
from app.database.repo import shifts as shift_repo
from app.database.repo import tasks as task_repo 
from app.config import DB_PATH, TZ

def calculate_duration(start_str: str):
    start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.now(TZ).replace(tzinfo=None)
    duration = end_dt - start_dt
    hours = int(duration.total_seconds() // 3600)
    minutes = int((duration.total_seconds() % 3600) // 60)
    return hours, minutes

def calculate_grade(user_duties_list, specific_duties):
    user_map = {item['title']: item['done'] for item in user_duties_list}
    
    missed = []
    # Проверяем только задачи, которые относятся к этому типу смены
    for duty_name in specific_duties:
        if not user_map.get(duty_name, False):
            missed.append(duty_name)
            
    total = len(specific_duties)
    done = total - len(missed)
    efficiency = int((done / total) * 100) if total > 0 else 0
    
    if efficiency == 100: grade = "⭐⭐⭐ (Идеально)"
    elif efficiency >= 80: grade = "⭐⭐ (Хорошо)"
    else: grade = "⚠️ (Внимание!)"
    
    return efficiency, grade, missed

async def toggle_duty(tg_id: int, task_index: int, is_checked: bool, tasks_list: list):
    active = await shift_repo.get_active_shift(tg_id)
    if not active: return None

    # Берем название задачи из переданного списка
    try: task_name = tasks_list[task_index]
    except IndexError: return None 

    try: 
        data = json.loads(active['report']) if active['report'] else {}
    except json.JSONDecodeError:
        data = {}

    if 'duties' not in data: data['duties'] = []
    
    found = False
    for t in data['duties']:
        if t['title'] == task_name:
            t['done'] = is_checked
            found = True
            break
    if not found and is_checked:
        data['duties'].append({"title": task_name, "done": True})

    new_report = json.dumps(data)
    await shift_repo.update_shift_report(active['id'], new_report)
    return [t['title'] for t in data['duties'] if t['done']]

async def close_shift_logic(tg_id: int, raw_data: str, user_name: str, tasks_list: list):
    active_shift = await shift_repo.get_active_shift(tg_id)
    if not active_shift: return None

    await shift_repo.end_shift(active_shift['id'], raw_data)
    
    try:
        data = json.loads(raw_data)
    except json.JSONDecodeError:
        data = {}

    comm_duties = data.get('comment_duties', "")     
    comm_products = data.get('comment_products', "") 
    hours, minutes = calculate_duration(active_shift['started_at'])
    
    # Считаем эффективность только для статистики
    efficiency, grade, missed_duties = calculate_grade(data.get('duties', []), tasks_list)

    time_str = f"{hours}ч {minutes}мин"
    
    # 👇 Я СПЕЦИАЛЬНО ИЗМЕНИЛ ЗАГОЛОВОК, ЧТОБЫ ТЫ УВИДЕЛА ИЗМЕНЕНИЯ
    user_report = (
        f"📊 <b>ФИНАЛЬНЫЙ ОТЧЕТ #{active_shift['id']}</b>\n"
        f"➖➖➖➖➖➖➖➖\n"
        f"👤 <b>Сотрудник:</b> {user_name}\n"
        f"🕒 <b>Длительность:</b> {time_str}\n"
        f"📈 <b>Эффективность:</b> {efficiency}% {grade}\n"
        f"➖➖➖➖➖➖➖➖\n"
    )
    
    if missed_duties:
        user_report += "<b>❌ НЕ ВЫПОЛНЕНО:</b>\n" + "\n".join(f"— {t}" for t in missed_duties) + "\n\n"
    else:
        user_report += "✅ <i>Все задачи выполнены!</i>\n\n"
        
    if comm_duties.strip():
        user_report += f"💬 <b>Заметка:</b> <i>«{comm_duties.strip()}»</i>\n\n"

    # Обработка закупки (продукты)
    products = data.get('products') 
    admin_buy_msg = None
    missing_list = []
    if products:
        missing_products = [p['title'] for p in products if not p['done']]
        missing_list = missing_products 
        admin_buy_msg = f"🛒 <b>ЗАКУПКА ({user_name}):</b>\n"
        if comm_products.strip():
             admin_buy_msg += f"❗️ <b>КОММЕНТАРИЙ:</b> «{comm_products.strip()}»\n\n"
        if missing_products:
            buy_list = "\n".join(f"{p}" for p in missing_products)
            admin_buy_msg += f"<i>(список для копирования):</i>\n<code>{buy_list}</code>"
        else:
            admin_buy_msg += "✅ <b>Все продукты в наличии!</b>\n(Докупать ничего не нужно)"

    # Авто-отмена задач
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE extra_tasks SET status = 'canceled' WHERE assigned_to = ? AND status = 'pending'", 
            (tg_id,)
        )
        await db.commit()

    return {
        "user_report": user_report,
        "admin_buy_msg": admin_buy_msg,
        "colleagues_rewarded": [], 
        "reward_amount": 0,
        "employee_name": user_name,
        "missing_list": missing_list
    }