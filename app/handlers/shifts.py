import json
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from app.core.config import WEB_APP_URL, TZ
from app.database.repo import users as user_repo
from app.database.repo import shifts as shift_repo
from app.database.repo import checklists as check_repo
from app.database.repo import roles as role_repo
from app.database.repo import tasks as task_repo 
from app.services import shift as shift_service
from app.keyboards import reply, builders
from app.states.states import ShiftState 

router = Router()

@router.message(StateFilter(ShiftState), F.text == "❌ Отмена")
async def cancel_shift_action(message: Message, state: FSMContext, restaurant_id: int):
    await state.clear()
    active = await shift_repo.get_active_shift(message.from_user.id, restaurant_id)
    if active:
        await message.answer("Действие отменено.", reply_markup=reply.menu_shift_open(WEB_APP_URL))
    else:
        await message.answer("Действие отменено.", reply_markup=reply.menu_shift_closed())


@router.message(F.text == "🟢 Начать смену")
async def start_shift_ask_type(message: Message, state: FSMContext, restaurant_id: int):
    tg_id = message.from_user.id
    if await shift_repo.get_active_shift(tg_id, restaurant_id):
        return await message.answer("⚠️ Смена уже идет!", reply_markup=reply.menu_shift_open(WEB_APP_URL))
    
    await state.set_state(ShiftState.waiting_for_shift_type)
    await message.answer("📅 <b>Выберите тип смены:</b>", reply_markup=reply.shift_type_kb())

@router.message(ShiftState.waiting_for_shift_type)
async def set_shift_type(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        return await message.answer("Отменено.", reply_markup=reply.menu_shift_closed())
    
    type_map = {"🌅 Утренняя": "morning", "🌇 Вечерняя": "evening", "📅 Полный день": "full"}
    selected = type_map.get(message.text)
    
    if not selected: 
        return await message.answer("❌ Нажмите на кнопку внизу!")
    
    await state.update_data(shift_type=selected)
    await state.set_state(ShiftState.waiting_for_photo_start)
    await message.answer("🎥 <b>Запишите видео-кружок</b> для открытия смены.", reply_markup=reply.cancel())

@router.message(ShiftState.waiting_for_photo_start, ~F.video_note)
async def start_wrong_media(message: Message):
    await message.answer("❌ <b>Ошибка!</b>\nЯ жду <b>ВИДЕО-КРУЖОК</b>.\nЗапишите кружок или нажмите «Отмена».")

@router.message(ShiftState.waiting_for_photo_start, F.video_note)
async def start_shift_with_video(message: Message, state: FSMContext, restaurant_id: int):
    tg_id = message.from_user.id
    video_note_id = message.video_note.file_id
    
    user_info = await user_repo.get_user(tg_id, restaurant_id)
    if not user_info:
        await state.clear()
        return await message.answer("Ошибка: Сотрудник не найден.")
    
    role = user_info['role']
    data = await state.get_data()
    shift_type = data.get('shift_type', 'full')
    
    await shift_repo.start_shift(tg_id, restaurant_id, role, shift_type)
    await message.answer("☀️ <b>Смена открыта!</b>", reply_markup=reply.menu_shift_open(WEB_APP_URL))
    await state.clear()
    
    roles_map = await role_repo.get_roles_map(restaurant_id)
    r_name = roles_map.get(role, role)
    type_rus = {"morning": "Утро", "evening": "Вечер", "full": "Полная"}.get(shift_type, shift_type)
    time_now = datetime.now(TZ).strftime('%H:%M')

    for admin_id in await user_repo.get_admins_ids(restaurant_id):
        try:
            await message.bot.send_video_note(admin_id, video_note_id)
            await message.bot.send_message(admin_id, f"☀️ <b>СМЕНА ОТКРЫТА ({type_rus})</b>\n👤 {user_info['full_name']} (<b>{r_name}</b>)\n📅 {time_now}")
        except: pass


@router.message(F.text == "⚡️ Онлайн Чек-лист")
async def open_live_checklist(message: Message, restaurant_id: int):
    tg_id = message.from_user.id
    active = await shift_repo.get_active_shift(tg_id, restaurant_id)
    if not active: return await message.answer("Смена не открыта.")
    
    tasks_list = await check_repo.get_checklist(restaurant_id, active['role'], active['shift_type'])
    
    try:
        data = json.loads(active['report']) if active['report'] else {}
        user_duties = data.get('duties', [])
    except: 
        user_duties = []
    
    status_list = []
    for i in range(len(tasks_list)):
        if i < len(user_duties):
            status_list.append(user_duties[i].get('done', False))
        else:
            status_list.append(False)
    
    roles_map = await role_repo.get_roles_map(restaurant_id)
    r_name = roles_map.get(active['role'], active['role'])
    
    await message.answer(
        f"⚡️ <b>Чек-лист: {r_name}</b>", 
        reply_markup=builders.checklist_kb(status_list, active['id'], tasks_list)
    )

@router.callback_query(F.data.startswith("check_"))
async def toggle_task_handler(callback: CallbackQuery, restaurant_id: int):
    parts = callback.data.split(":")
    action, index_str, btn_shift_id = parts[0], parts[1], int(parts[2])
    active = await shift_repo.get_active_shift(callback.from_user.id, restaurant_id)
    if not active or active['id'] != btn_shift_id: return await callback.answer("Смена закрыта!", show_alert=True)
    
    tasks_list = await check_repo.get_checklist(restaurant_id, active['role'], active['shift_type'])
    
    if int(index_str) >= len(tasks_list):
        return await callback.answer("Список изменился, откройте заново.")

    status_list = await shift_service.toggle_duty(callback.from_user.id, restaurant_id, int(index_str), (action == "check_on"), tasks_list)
    
    if status_list is not None:
        try: 
            await callback.message.edit_reply_markup(
                reply_markup=builders.checklist_kb(status_list, active['id'], tasks_list)
            )
        except: pass 

@router.callback_query(F.data.startswith("submit_checklist"))
async def submit_checklist_ask_comment(callback: CallbackQuery, state: FSMContext, restaurant_id: int):
    shift_id = int(callback.data.split(":")[1])
    active = await shift_repo.get_active_shift(callback.from_user.id, restaurant_id)
    if not active or active['id'] != shift_id: return await callback.answer("Смена закрыта!", show_alert=True)
    
    await state.update_data(current_shift_id=shift_id)
    await state.set_state(ShiftState.waiting_checklist_comment)
    
    await callback.message.answer(
        "📝 <b>Хотите добавить комментарий к отчету?</b>\nНапишите текст или нажмите «Пропустить».",
        reply_markup=reply.comment_menu()
    )
    await callback.answer()

@router.message(ShiftState.waiting_checklist_comment)
async def submit_checklist_process(message: Message, state: FSMContext, restaurant_id: int):
    if message.text == "❌ Отмена":
        await state.clear()
        return await message.answer("Отменено.", reply_markup=reply.menu_shift_open(WEB_APP_URL))

    comment = message.text if message.text != "➡️ Пропустить" else None
    
    data = await state.get_data()
    shift_id = data.get('current_shift_id')
    
    active = await shift_repo.get_active_shift(message.from_user.id, restaurant_id)
    if not active or active['id'] != shift_id: 
        await state.clear()
        return await message.answer("Смена уже неактивна.", reply_markup=reply.menu_shift_open(WEB_APP_URL))

    tasks_list = await check_repo.get_checklist(restaurant_id, active['role'], active['shift_type'])
    try:
        data_report = json.loads(active['report']) if active['report'] else {}
        user_duties = data_report.get('duties', [])
    except: user_duties = []
    
    completed_count = 0
    visual = ""
    for i, task in enumerate(tasks_list):
        is_done = False
        if i < len(user_duties):
            is_done = user_duties[i].get('done', False)
        
        if is_done:
            visual += f"✅ {task}\n"
            completed_count += 1
        else:
            visual += f"🟥 {task}\n"
    
    total = len(tasks_list)
    percent = int((completed_count / total) * 100) if total > 0 else 0
    
    user = await user_repo.get_user(message.from_user.id, restaurant_id)
    roles_map = await role_repo.get_roles_map(restaurant_id)
    r_name = roles_map.get(active['role'], active['role'])
    
    msg_text = (
        f"🔔 <b>ПРОМЕЖУТОЧНЫЙ ОТЧЕТ</b>\n"
        f"👤 <b>Сотрудник:</b> {user['full_name']} (<b>{r_name}</b>)\n"
        f"📅 <b>Смена:</b> {active['shift_type']}\n"
        f"📊 <b>Выполнено:</b> {completed_count}/{total} ({percent}%)\n"
    )
    if comment:
        msg_text += f"💬 <b>Комментарий:</b> {comment}\n"
    
    msg_text += f"\n{visual}"

    for admin_id in await user_repo.get_admins_ids(restaurant_id):
        try:
            await message.bot.send_message(admin_id, msg_text)
        except: pass
    
    await state.clear()
    await message.answer("✅ Отчет отправлен!", reply_markup=reply.menu_shift_open(WEB_APP_URL))


@router.message(F.text == "🔴 Закончить смену")
async def end_shift_ask_comment(message: Message, state: FSMContext, restaurant_id: int):
    if not await shift_repo.get_active_shift(message.from_user.id, restaurant_id): return await message.answer("Нет активной смены.")
    await state.set_state(ShiftState.waiting_end_comment)
    await message.answer(
        "📝 <b>Есть что добавить перед закрытием?</b>\nНапишите итоги, проблемы или нажмите «Пропустить».",
        reply_markup=reply.comment_menu()
    )

@router.message(ShiftState.waiting_end_comment)
async def end_shift_process_comment(message: Message, state: FSMContext):
    comment = message.text if message.text != "➡️ Пропустить" else None
    await state.update_data(end_comment=comment)
    
    await state.set_state(ShiftState.waiting_for_photo_end)
    await message.answer("🎥 <b>Теперь запишите видео-кружок</b> для закрытия.", reply_markup=reply.cancel())

@router.message(ShiftState.waiting_for_photo_end, ~F.video_note)
async def end_wrong_media(message: Message):
    await message.answer("❌ <b>Ошибка!</b>\nОтправьте <b>ВИДЕО-КРУЖОК</b> для закрытия.")

@router.message(ShiftState.waiting_for_photo_end, F.video_note)
async def end_shift_with_video(message: Message, state: FSMContext, restaurant_id: int):
    tg_id = message.from_user.id
    video_note_id = message.video_note.file_id
    
    data = await state.get_data()
    end_comment = data.get('end_comment')

    active = await shift_repo.get_active_shift(tg_id, restaurant_id)
    if not active:
        await state.clear()
        return await message.answer("Смена уже закрыта.")
    
    user_info = await user_repo.get_user(tg_id, restaurant_id)
    tasks_list = await check_repo.get_checklist(restaurant_id, active['role'], active['shift_type'])
    
    result = await shift_service.close_shift_logic(tg_id, restaurant_id, active['report'] or "{}", user_info['full_name'], tasks_list, end_comment)
    
    await message.answer(result['user_report'], reply_markup=reply.menu_shift_closed())
    await state.clear()
    
    for admin_id in await user_repo.get_admins_ids(restaurant_id):
        try:
            await message.bot.send_video_note(admin_id, video_note_id)
            await message.bot.send_message(admin_id, result['user_report'])
        except: pass

@router.message(F.text == "💰 Мой баланс")
async def balance_btn(message: Message, restaurant_id: int):
    balance = await task_repo.get_balance(message.from_user.id, restaurant_id)
    await message.answer(f"💳 <b>Ваш бонусный счет:</b>\n\n💎 <b>{balance} баллов</b>")

@router.message(F.text == "📜 История смен")
async def history_btn(message: Message, restaurant_id: int):
    shifts = await shift_repo.get_last_shifts(message.from_user.id, restaurant_id)
    if shifts: text = "🗓 <b>Последние смены:</b>\n\n" + "\n".join(f"🔹 {s['started_at']} ({s.get('shift_type', 'full')})" for s in shifts)
    else: text = "📭 История пуста."
    await message.answer(text)