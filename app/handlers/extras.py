from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from app.config import TZ
from app.database.repo import users as user_repo, tasks as task_repo, shifts as shift_repo
from app.keyboards import builders, reply
from app.states import TaskState
from app.services import tasks as task_service

router = Router()

@router.message(StateFilter(TaskState), F.text == "❌ Отмена")
async def cancel_global_text(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=reply.admin_main())

@router.callback_query(F.data == "cancel_task")
async def cancel_global_inline(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Отменено.", reply_markup=reply.admin_main())

@router.message(F.text == "📝 Дать задание")
async def start_task(message: Message, state: FSMContext):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    await state.set_state(TaskState.waiting_text)
    await message.answer("✍️ Текст задания:", reply_markup=reply.cancel())

@router.message(TaskState.waiting_text)
async def task_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await state.set_state(TaskState.waiting_reward)
    await message.answer("💰 Награда (число):")

@router.message(TaskState.waiting_reward)
async def task_reward(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("❌ Только число!")
    await state.update_data(reward=int(message.text))
    await state.set_state(TaskState.waiting_hours) 
    await message.answer("⏳ Срок (мин или '1ч'):")

@router.message(TaskState.waiting_hours)
async def task_deadline_parse(message: Message, state: FSMContext):
    raw_text = message.text.lower().strip()
    text_nums = raw_text.replace('ч', '').replace('h', '')
    try:
        if 'ч' in raw_text or 'h' in raw_text:
            hours = float(text_nums)
            minutes = int(hours * 60)
            display_str = f"{hours} ч."
        else:
            minutes = int(text_nums)
            display_str = f"{minutes} мин."
        if minutes <= 0: raise ValueError
    except: 
        return await message.answer("❌ Введите минуты (30) или часы (1ч).")
    
    deadline = (datetime.now(TZ) + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
    await state.update_data(deadline=deadline, time_display=display_str)
    
    active_ids = [s['user_id'] for s in await shift_repo.get_all_active_shifts_data()]
    await state.set_state(TaskState.waiting_employee)
    await message.answer("👉 Кому?", reply_markup=builders.task_assign_menu(await user_repo.get_all_users(), message.from_user.id, active_ids))

@router.callback_query(TaskState.waiting_employee, F.data.startswith("assign:"))
async def task_finish(callback: CallbackQuery, state: FSMContext, bot: Bot):
    target_id = int(callback.data.split(":")[1])
    active_shifts = await shift_repo.get_all_active_shifts_data()
    active_ids = [s['user_id'] for s in active_shifts]
    
    if target_id not in active_ids:
        await callback.answer("⛔ ОШИБКА: Сотрудник не на смене!", show_alert=True)
        return

    data = await state.get_data()
    task_id = await task_repo.create_personal_task_with_deadline(
        data['text'], data['reward'], data['deadline'], target_id
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Я выполнил!", callback_data=f"done_task:{task_id}")]])
    
    try:
        msg_text = (
            f"⚡️ <b>ЗАДАНИЕ!</b>\n"
            f"📝 {data['text']}\n"
            f"⏳ Срок: {data['time_display']}\n"
            f"💰 Награда: +{data['reward']} баллов"
        )
        sent_msg = await bot.send_message(target_id, msg_text, reply_markup=kb)
        await task_repo.set_task_message_id(task_id, sent_msg.message_id)

        await callback.message.delete()
        await callback.message.answer("✅ Отправлено.", reply_markup=reply.admin_main())
    except Exception as e:
        await callback.message.edit_text(f"Ошибка: {e}")
    await state.clear()

@router.message(F.text == "🗑 Отменить задание")
async def cancel_task_menu(message: Message):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    tasks = await task_repo.get_pending_tasks_details()
    if not tasks: return await message.answer("Нет заданий.")

    b = builders.InlineKeyboardBuilder()
    for t in tasks: b.button(text=f"❌ {t['text']} ({t['full_name']})", callback_data=f"admin_cancel:{t['id']}")
    b.button(text="🔙 Закрыть", callback_data="close_checklist")
    b.adjust(1)
    await message.answer("Выберите:", reply_markup=b.as_markup())

@router.callback_query(F.data.startswith("admin_cancel:"))
async def admin_cancel(callback: CallbackQuery, bot: Bot):
    tid = int(callback.data.split(":")[1])
    task = await task_repo.get_task_details(tid)
    await task_repo.cancel_task_in_db(tid)
    
    if task and task['message_id']:
        try:
            new_text = (
                f"🚫 <b>ЗАДАЧА ОТМЕНЕНА</b>\n"
                f"📝 {task['text']}\n"
                f"❌ <i>Администратор аннулировал это задание.</i>"
            )
            await bot.edit_message_text(
                text=new_text,
                chat_id=task['assigned_to'],
                message_id=task['message_id'],
                reply_markup=None
            )
        except: pass

    await callback.answer("Отменено.")
    await callback.message.edit_text("🗑 Задача отменена.")

@router.message(F.text == "📋 История заданий")
async def history(message: Message):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    tasks = await task_repo.get_tasks_history()
    text = "📋 <b>Последние задания:</b>\n\n"
    for t in tasks:
        icon = {"completed": "✅", "expired": "❌", "canceled": "🚫"}.get(t['status'], "⏳")
        text += f"{icon} {t['text']} ({t['full_name']})\n"
    await message.answer(text if tasks else "📭 Пусто.")

@router.callback_query(F.data.startswith("done_task:"))
async def complete_task(callback: CallbackQuery):
    reward, text = await task_service.try_complete_task(int(callback.data.split(":")[1]))
    
    if reward > 0:
        await callback.message.edit_text(f"✅ ВЫПОЛНЕНО!\n💰 +{reward} баллов")
        
        user_info = await user_repo.get_user(callback.from_user.id)
        worker_name = user_info['full_name'] if user_info else callback.from_user.full_name
        
        admin_report = (
            f"🔔 <b>ЗАДАЧА ВЫПОЛНЕНА!</b>\n\n"
            f"👤 <b>Кто:</b> {worker_name}\n"
            f"📝 <b>Задача:</b> {text}\n"
            f"💰 <b>Награда:</b> {reward} баллов"
        )
        for admin in await user_repo.get_admins_ids():
            try: await callback.bot.send_message(admin, admin_report)
            except: pass
            
    elif reward == -1: 
        await callback.message.delete()
        await callback.answer("⏳ Время истекло!", show_alert=True)
    else: 
        await callback.message.delete()
        await callback.answer("Уже неактуально.", show_alert=True)