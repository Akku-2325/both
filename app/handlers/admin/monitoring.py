import json
from datetime import datetime
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
    
    for i, task_data in enumerate(tasks):
        task_text = task_data['text']
        item_type = task_data.get('item_type', 'simple')
        
        is_done = False
        if i < len(user_duties):
            is_done = user_duties[i].get('done', False)
        
        type_icon = ""
        if item_type == 'photo': type_icon = "📸 "
        elif item_type == 'video': type_icon = "🎥 "

        if is_done:
            visual += f"✅ {type_icon}{task_text}\n"
            completed_count += 1
        else:
            visual += f"🟥 {type_icon}{task_text}\n"
    
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

@router.message(F.text == "📜 Журнал смен")
async def cmd_shift_journal_start(message: Message):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    await message.answer("📜 <b>Журнал смен</b>\nВыберите формат просмотра:", reply_markup=builders.journal_type_menu())

@router.callback_query(F.data == "back_to_journal_type")
async def back_to_journal_type(callback: CallbackQuery):
    await callback.message.edit_text("📜 <b>Журнал смен</b>\nВыберите формат просмотра:", reply_markup=builders.journal_type_menu())

@router.callback_query(F.data == "journal_by_user")
async def journal_user_select_view(callback: CallbackQuery, restaurant_id: int):
    users = await user_repo.get_all_users(restaurant_id)
    await callback.message.edit_text("👤 <b>Выберите сотрудника:</b>", reply_markup=builders.journal_user_select(users))

@router.callback_query(F.data.startswith("journal_all:"))
async def journal_all_pages(callback: CallbackQuery, restaurant_id: int):
    page = int(callback.data.split(":")[1])
    per_page = 10
    total_count = await shift_repo.count_total_shifts(restaurant_id)
    total_pages = (total_count + per_page - 1) // per_page
    if total_count == 0: return await callback.answer("История пуста.", show_alert=True)
    shifts = await shift_repo.get_shifts_paginated(restaurant_id, page, per_page)
    text = f"📜 <b>Все смены ({total_count}):</b>\n\n"
    for s in shifts:
        start = datetime.strptime(s['started_at'], "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(s['ended_at'], "%Y-%m-%d %H:%M:%S")
        diff = end - start
        duration = f"{int(diff.total_seconds() // 3600)}ч {int((diff.total_seconds() % 3600) // 60)}м"
        text += f"📅 <b>{start.strftime('%d.%m')}</b> | {s['full_name']}\n🕘 {start.strftime('%H:%M')} - {end.strftime('%H:%M')} ({duration})\n──────────────────\n"
    await callback.message.edit_text(text, reply_markup=builders.shift_history_kb(page, total_pages))

@router.callback_query(F.data == "confirm_clear_shifts")
async def ask_clear_history(callback: CallbackQuery):
    builder = builders.InlineKeyboardBuilder()
    builder.button(text="🔥 ДА, УДАЛИТЬ ВСЁ", callback_data="clear_history_final")
    builder.button(text="🔙 Отмена", callback_data="back_to_journal_type")
    builder.adjust(1)
    await callback.message.edit_text("⚠️ <b>ВНИМАНИЕ!</b>\nВы хотите удалить ВСЮ историю закрытых смен.", reply_markup=builder.as_markup())

@router.callback_query(F.data == "clear_history_final")
async def clear_history_execute(callback: CallbackQuery, restaurant_id: int):
    await shift_repo.clear_all_restaurant_shifts(restaurant_id)
    await callback.answer("✅ Журнал смен очищен", show_alert=True)
    await back_to_journal_type(callback)