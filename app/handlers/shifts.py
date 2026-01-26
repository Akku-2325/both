import json
import aiosqlite
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.config import WEB_APP_URL, DB_PATH, TZ
from app.data import get_tasks  
from app.database.repo import users as user_repo
from app.database.repo import shifts as shift_repo
from app.database.repo import tasks as task_repo

from app.services import shift as shift_service
from app.keyboards import reply, builders
from app.states import ShiftState 

router = Router()

@router.message(F.text == "🟢 Начать смену")
async def start_shift_ask_type(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    
    if await shift_repo.get_active_shift(tg_id):
        return await message.answer("⚠️ Смена уже идет!", reply_markup=reply.menu_shift_open(WEB_APP_URL))
    
    await state.set_state(ShiftState.waiting_for_shift_type)
    await message.answer("📅 <b>Выберите тип смены:</b>", reply_markup=reply.shift_type_kb())

@router.message(ShiftState.waiting_for_shift_type)
async def set_shift_type(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        return await message.answer("Отменено.", reply_markup=reply.menu_shift_closed())
    
    type_map = {
        "🌅 Утренняя": "morning",
        "🌇 Вечерняя": "evening",
        "📅 Полный день": "full"
    }
    
    selected = type_map.get(message.text)
    
    if not selected:
        return await message.answer("❌ Нажмите на кнопку внизу!")
    
    await state.update_data(shift_type=selected)
    
    await state.set_state(ShiftState.waiting_for_photo_start)
    await message.answer("🎥 <b>Запишите видео-кружок</b> для открытия смены.", reply_markup=reply.cancel())

@router.message(ShiftState.waiting_for_photo_start, F.video_note)
async def start_shift_with_video(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    video_note_id = message.video_note.file_id
    
    user_info = await user_repo.get_user(tg_id)
    if not user_info:
        await state.clear()
        return await message.answer("Ошибка: Сотрудник не найден.")
        
    role = user_info['role']
    
    data = await state.get_data()
    shift_type = data.get('shift_type', 'full')

    await shift_repo.start_shift(tg_id, role, shift_type)
    
    await message.answer("☀️ <b>Смена открыта!</b>", reply_markup=reply.menu_shift_open(WEB_APP_URL))
    await state.clear()

    name = user_info['full_name']
    
    type_rus = {"morning": "Утро", "evening": "Вечер", "full": "Полная"}.get(shift_type, shift_type)
    time_now = datetime.now(TZ).strftime('%H:%M')

    for admin_id in await user_repo.get_admins_ids():
        try:
            await message.bot.send_video_note(admin_id, video_note_id)
            await message.bot.send_message(
                admin_id, 
                f"☀️ <b>СМЕНА ОТКРЫТА ({type_rus})</b>\n"
                f"👤 {name} ({role})\n"
                f"📅 {time_now}"
            )
        except: pass

@router.message(ShiftState.waiting_for_photo_start, F.text == "❌ Отмена")
async def cancel_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отмена.", reply_markup=reply.menu_shift_closed())

@router.message(ShiftState.waiting_for_photo_start)
async def start_wrong_media(message: Message): 
    await message.answer("❌ Нужно отправить именно <b>видео-кружок</b> (или нажмите Отмена)!")

@router.message(F.text == "⚡️ Онлайн Чек-лист")
async def open_live_checklist(message: Message):
    tg_id = message.from_user.id
    
    active = await shift_repo.get_active_shift(tg_id)
    if not active: 
        return await message.answer("Смена не открыта.")

    current_report = active['report'] 
    try:
        data = json.loads(current_report) if current_report else {}
        completed = [t['title'] for t in data.get('duties', []) if t['done']]
    except json.JSONDecodeError: 
        completed = []

    tasks_list = get_tasks(active['role'], active['shift_type'])

    await message.answer(
        "⚡️ <b>Ваш Чек-лист:</b>", 
        reply_markup=builders.checklist_kb(completed, active['id'], tasks_list)
    )

@router.callback_query(F.data.startswith("check_"))
async def toggle_task_handler(callback: CallbackQuery):
    try:
        parts = callback.data.split(":")
        action = parts[0]
        index_str = parts[1]
        btn_shift_id = int(parts[2])
    except: 
        return await callback.answer("Ошибка данных кнопки.")

    active = await shift_repo.get_active_shift(callback.from_user.id)
    if not active or active['id'] != btn_shift_id:
        return await callback.answer("Эта смена уже закрыта!", show_alert=True)

    tasks_list = get_tasks(active['role'], active['shift_type'])

    is_on = (action == "check_on")
    
    completed_list = await shift_service.toggle_duty(callback.from_user.id, int(index_str), is_on, tasks_list)
    
    if completed_list is None: 
        return await callback.answer("Ошибка обновления.")

    try:
        await callback.message.edit_reply_markup(
            reply_markup=builders.checklist_kb(completed_list, active['id'], tasks_list)
        )
    except: 
        pass 

@router.callback_query(F.data.startswith("submit_checklist"))
async def submit_checklist(callback: CallbackQuery):
    try:
        shift_id = int(callback.data.split(":")[1])
    except: 
        return await callback.answer("Ошибка ID.")

    tg_id = callback.from_user.id
    active = await shift_repo.get_active_shift(tg_id)
    
    if not active or active['id'] != shift_id:
        return await callback.answer("Смена закрыта или чек-лист устарел.", show_alert=True)

    try:
        data = json.loads(active['report']) if active['report'] else {}
        done_titles = [t['title'] for t in data.get('duties', []) if t['done']]
    except json.JSONDecodeError: 
        done_titles = []

    tasks_list = get_tasks(active['role'], active['shift_type'])

    total = len(tasks_list)
    completed_count = 0
    visual = ""
    
    for task in tasks_list:
        if task in done_titles:
            visual += f"✅ {task}\n"
            completed_count += 1
        else:
            visual += f"🟥 {task}\n"

    percent = int((completed_count / total) * 100) if total > 0 else 0

    user = await user_repo.get_user(tg_id)
    name = user['full_name']
    
    admins = await user_repo.get_admins_ids()
    sent_count = 0
    
    for admin_id in admins:
        try:
            await callback.bot.send_message(
                admin_id,
                f"🔔 <b>ПРОМЕЖУТОЧНЫЙ ОТЧЕТ</b>\n"
                f"👤 <b>Сотрудник:</b> {name} ({active['role']})\n"
                f"📅 <b>Смена:</b> {active['shift_type']}\n"
                f"📊 <b>Выполнено:</b> {completed_count}/{total} ({percent}%)\n\n"
                f"{visual}\n"
                f"ℹ️ <i>Смена еще продолжается.</i>"
            )
            sent_count += 1
        except: pass
    
    if sent_count > 0:
        await callback.answer(f"✅ Отчет отправлен {sent_count} админам!", show_alert=True)
    else:
        await callback.answer("Не удалось отправить (нет админов).", show_alert=True)

@router.callback_query(F.data == "close_checklist")
async def close_check(c: CallbackQuery): 
    await c.message.delete()

@router.message(F.text == "🔴 Закончить смену")
async def end_shift_ask_video(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    if not await shift_repo.get_active_shift(tg_id):
        return await message.answer("Нет активной смены.")

    await state.set_state(ShiftState.waiting_for_photo_end)
    await message.answer("🎥 <b>Запишите видео-кружок</b> для закрытия (чистая зона).", reply_markup=reply.cancel())

@router.message(ShiftState.waiting_for_photo_end, F.video_note)
async def end_shift_with_video(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    video_note_id = message.video_note.file_id
    
    active = await shift_repo.get_active_shift(tg_id)
    if not active:
        await state.clear()
        return await message.answer("Смена уже закрыта.")
    
    user_info = await user_repo.get_user(tg_id)
    
    tasks_list = get_tasks(active['role'], active['shift_type'])
    
    result = await shift_service.close_shift_logic(
        tg_id, 
        active['report'] or "{}", 
        user_info['full_name'], 
        tasks_list
    )

    await message.answer(result['user_report'], reply_markup=reply.menu_shift_closed())
    if result.get('admin_buy_msg'): 
        await message.answer(result['admin_buy_msg'])
        
    await state.clear()

    for admin_id in await user_repo.get_admins_ids():
        try:
            await message.bot.send_video_note(admin_id, video_note_id)
            await message.bot.send_message(
                admin_id, 
                f"🏁 <b>СМЕНА ЗАКРЫТА</b>\n👤 {user_info['full_name']}"
            )
            await message.bot.send_message(admin_id, result['user_report'])
            
            if result.get('admin_buy_msg'):
                await message.bot.send_message(admin_id, result['admin_buy_msg'])
        except: pass

@router.message(ShiftState.waiting_for_photo_end, F.text == "❌ Отмена")
async def cancel_end(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отмена.", reply_markup=reply.menu_shift_open(WEB_APP_URL))

@router.message(ShiftState.waiting_for_photo_end)
async def end_wrong_media(message: Message): 
    await message.answer("❌ Отправьте <b>видео-кружок</b>!")

@router.message(F.text == "💰 Мой баланс")
async def balance_btn(message: Message):
    balance = await task_repo.get_balance(message.from_user.id)
    await message.answer(f"💳 <b>Ваш бонусный счет:</b>\n\n💎 <b>{balance} баллов</b>")

@router.message(F.text == "📜 История смен")
async def history_btn(message: Message):
    shifts = await shift_repo.get_last_shifts(message.from_user.id)
    if shifts:
        text = "🗓 <b>Последние смены:</b>\n\n" + "\n".join(
            f"🔹 {s['started_at']} ({s.get('shift_type', 'full')})" for s in shifts
        )
    else:
        text = "📭 История пуста."
    await message.answer(text)

@router.message(F.text == "❌ Аварийное закрытие")
async def force_close(message: Message):
    active = await shift_repo.get_active_shift(message.from_user.id)
    if active:
        await shift_repo.end_shift(active['id'], "{}")
        await message.answer("🔴 Смена закрыта принудительно.", reply_markup=reply.menu_shift_closed())
    else:
        await message.answer("Нет активной смены.", reply_markup=reply.menu_shift_closed())