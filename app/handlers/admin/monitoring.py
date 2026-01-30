import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from app.database.repo import users as user_repo, shifts as shift_repo, checklists as check_repo, roles as role_repo
from app.keyboards import builders

router = Router()

@router.message(F.text == "👀 Мониторинг")
async def monitor_menu(message: Message, restaurant_id: int):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    shifts = await shift_repo.get_all_active_shifts_data(restaurant_id)
    roles_map = await role_repo.get_roles_map(restaurant_id)
    
    if not shifts: return await message.answer("🤷‍♂️ Сейчас нет активных смен.")
    
    await message.answer("🔎 <b>Выберите сотрудника для просмотра:</b>", reply_markup=builders.active_shifts_menu(shifts, roles_map))

@router.callback_query(F.data == "refresh_monitor")
async def refresh_monitor_list(callback: CallbackQuery, restaurant_id: int):
    shifts = await shift_repo.get_all_active_shifts_data(restaurant_id)
    roles_map = await role_repo.get_roles_map(restaurant_id)
    
    try:
        if not shifts: 
            await callback.message.edit_text("🤷‍♂️ Все смены закрыты.", reply_markup=None)
        else:
            await callback.message.edit_text("🔎 <b>Выберите сотрудника:</b>", reply_markup=builders.active_shifts_menu(shifts, roles_map))
    except TelegramBadRequest:
        await callback.answer("Данные не изменились")

@router.callback_query(F.data.startswith("monitor:"))
async def monitor_specific_user(callback: CallbackQuery, restaurant_id: int):
    target_id = int(callback.data.split(":")[1])
    active = await shift_repo.get_active_shift(target_id, restaurant_id)
    if not active:
        await callback.answer("Смена уже закрыта!", show_alert=True)
        return await refresh_monitor_list(callback, restaurant_id)
    
    user = await user_repo.get_user(target_id, restaurant_id)
    roles_map = await role_repo.get_roles_map(restaurant_id)
    r_name = roles_map.get(active['role'], active['role'])
    
    tasks = await check_repo.get_checklist(restaurant_id, active['role'], active['shift_type'])
    
    try:
        data = json.loads(active['report']) if active['report'] else {}
        user_duties = data.get('duties', [])
    except: 
        user_duties = []
    
    visual = ""
    completed_count = 0
    
    for i, task_title in enumerate(tasks):
        is_done = False
        if i < len(user_duties):
            is_done = user_duties[i].get('done', False)
        
        if is_done:
            visual += f"✅ {task_title}\n"
            completed_count += 1
        else:
            visual += f"🟥 {task_title}\n"
    
    total = len(tasks)
    perc = int((completed_count / total) * 100) if total > 0 else 0
    
    blocks = perc // 10
    progress = "🟩" * blocks + "⬜️" * (10 - blocks)
    
    text = (
        f"👤 <b>{user['full_name']}</b> (<b>{r_name}</b>)\n"
        f"📊 Прогресс: {completed_count}/{total} ({perc}%)\n"
        f"{progress}\n\n"
        f"{visual}\n"
        f"👇 <i>Нажмите «Обновить», чтобы увидеть изменения</i>"
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=builders.back_to_monitor())
    except TelegramBadRequest:
        await callback.answer("Ничего не изменилось")

@router.callback_query(F.data == "close_checklist")
async def close_check(c: CallbackQuery): 
    await c.message.delete()