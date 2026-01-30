import aiosqlite
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.exceptions import TelegramBadRequest

from app.core.config import TZ, DB_PATH
from app.database.repo import users as user_repo, tasks as task_repo, shifts as shift_repo, roles as role_repo
from app.keyboards import builders, reply
from app.states.states import TaskState
from app.services import tasks as task_service

router = Router()

@router.callback_query(F.data.startswith("done_task:"))
async def complete_task_handler(callback: CallbackQuery, restaurant_id: int):
    try:
        task_id = int(callback.data.split(":")[1])
        reward, text = await task_service.try_complete_task(task_id, restaurant_id)
        
        if reward > 0:
            await callback.message.edit_text(f"✅ <b>ВЫПОЛНЕНО!</b>\n💰 Вам начислено: +{reward} баллов")
            user = await user_repo.get_user(callback.from_user.id, restaurant_id)
            admin_msg = f"🔔 <b>ЗАДАЧА ВЫПОЛНЕНА!</b>\n👤 {user['full_name']}\n📝 {text}\n💰 +{reward}"
            for admin_id in await user_repo.get_admins_ids(restaurant_id):
                try: await callback.bot.send_message(admin_id, admin_msg)
                except: pass
        elif reward == -1:
            await callback.message.edit_text(f"⏳ <b>ВРЕМЯ ИСТЕКЛО!</b>\nВы не успели выполнить задачу вовремя.")
        else:
            await callback.answer("Эта задача уже неактуальна.", show_alert=True)
            await callback.message.delete()
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

@router.message(F.text == "📝 Задания")
async def tasks_main_menu(message: Message):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    kb = reply.ReplyKeyboardMarkup(
        keyboard=[
            [reply.KeyboardButton(text="📝 Дать задание"), reply.KeyboardButton(text="🗑 Отменить задание")],
            [reply.KeyboardButton(text="📜 История заданий")],
            [reply.KeyboardButton(text="🔙 В Главное меню")]
        ],
        resize_keyboard=True
    )
    await message.answer("📝 <b>Управление заданиями:</b>", reply_markup=kb)

@router.message(F.text == "📜 История заданий")
async def tasks_history(message: Message, restaurant_id: int):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    
    history = await task_repo.get_tasks_history(restaurant_id, limit=10)
    if not history:
        return await message.answer("📭 История пуста.")
        
    text = "📜 <b>Последние 10 заданий:</b>\n\n"
    for t in history:
        status_icon = {"completed": "✅", "expired": "⏳", "canceled": "🚫", "pending": "🕒"}.get(t['status'], "❓")
        text += f"{status_icon} <b>{t['full_name']}</b>: {t['text']} ({t['reward']})\n"
        
    await message.answer(text)

@router.message(F.text == "📝 Дать задание")
async def start_task(message: Message, state: FSMContext):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    await state.set_state(TaskState.waiting_text)
    await message.answer("✍️ Текст задания:", reply_markup=reply.cancel())

@router.message(StateFilter(TaskState), F.text == "❌ Отмена")
async def cancel_task_creation(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=reply.admin_main())

@router.message(TaskState.waiting_text)
async def task_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await state.set_state(TaskState.waiting_reward)
    await message.answer("💰 Награда (целое число):")

@router.message(TaskState.waiting_reward)
async def task_reward(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("❌ Введите число!")
    await state.update_data(reward=int(message.text))
    await state.set_state(TaskState.waiting_hours) 
    await message.answer("⏳ Срок выполнения (минуты, например 30, или часы '1ч'):")

@router.message(TaskState.waiting_hours)
async def task_deadline_parse(message: Message, state: FSMContext, restaurant_id: int):
    raw = message.text.lower().strip()
    try:
        if 'ч' in raw or 'h' in raw:
            mins = int(float(raw.replace('ч','').replace('h','')) * 60)
        else:
            mins = int(raw)
        if mins <= 0: raise ValueError
    except: return await message.answer("❌ Неверный формат. Пишите минуты (30) или часы (1ч).")
    
    deadline = (datetime.now(TZ) + timedelta(minutes=mins)).strftime("%Y-%m-%d %H:%M:%S")
    await state.update_data(deadline=deadline, time_display=message.text)
    
    active_shifts = await shift_repo.get_all_active_shifts_data(restaurant_id)
    if not active_shifts:
        await state.clear()
        return await message.answer("❌ <b>Ошибка:</b> Сейчас нет никого на смене.", reply_markup=reply.admin_main())

    active_ids = [s['user_id'] for s in active_shifts]
    users = await user_repo.get_all_users(restaurant_id)
    roles_map = await role_repo.get_roles_map(restaurant_id)
    
    await state.set_state(TaskState.waiting_employee)
    await message.answer("👉 Кому отправить задание?", reply_markup=builders.task_assign_menu(users, message.from_user.id, active_ids, roles_map))

@router.callback_query(TaskState.waiting_employee, F.data.startswith("assign:"))
async def task_finish(callback: CallbackQuery, state: FSMContext, bot: Bot, restaurant_id: int):
    target_id = int(callback.data.split(":")[1])
    active = await shift_repo.get_active_shift(target_id, restaurant_id)
    if not active:
        await callback.answer("⛔ ОШИБКА: Сотрудник уже закрыл смену!", show_alert=True)
        return

    data = await state.get_data()
    tid = await task_repo.create_personal_task_with_deadline(data['text'], data['reward'], data['deadline'], target_id, restaurant_id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Я выполнил!", callback_data=f"done_task:{tid}")]])
    
    try:
        msg_text = (
            f"⚡️ <b>НОВОЕ ЗАДАНИЕ!</b>\n\n"
            f"📝 {data['text']}\n"
            f"⏳ Срок: {data['time_display']}\n"
            f"💰 Награда: +{data['reward']} баллов"
        )
        sent_msg = await bot.send_message(target_id, msg_text, reply_markup=kb)
        await task_repo.set_task_message_id(tid, sent_msg.message_id)
        
        await callback.message.delete()
        await callback.message.answer("✅ Задание успешно отправлено.", reply_markup=reply.admin_main())
    except:
        await callback.message.answer("❌ Не удалось отправить (возможно бот заблокирован).")
    
    await state.clear()

@router.message(F.text == "🗑 Отменить задание")
async def cancel_task_menu(message: Message, restaurant_id: int):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    tasks = await task_repo.get_pending_tasks_details(restaurant_id)
    if not tasks: return await message.answer("Нет активных заданий.")

    b = builders.InlineKeyboardBuilder()
    for t in tasks:
        b.button(text=f"❌ {t['text'][:20]}... ({t['full_name']})", callback_data=f"admin_cancel:{t['id']}")
    b.button(text="🔙 Назад", callback_data="back_to_admin")
    b.adjust(1)
    await message.answer("Выберите задание для отмены:", reply_markup=b.as_markup())

@router.callback_query(F.data.startswith("admin_cancel:"))
async def admin_cancel(callback: CallbackQuery, bot: Bot, restaurant_id: int):
    tid = int(callback.data.split(":")[1])
    task = await task_repo.get_task_details(tid, restaurant_id)
    await task_repo.cancel_task_in_db(tid, restaurant_id)
    
    if task and task['message_id']:
        try:
            await bot.edit_message_text(
                chat_id=task['assigned_to'],
                message_id=task['message_id'],
                text=f"🚫 <b>ЗАДАЧА ОТМЕНЕНА АДМИНИСТРАТОРОМ</b>\n📝 {task['text']}",
                reply_markup=None
            )
        except: pass

    tasks = await task_repo.get_pending_tasks_details(restaurant_id)
    if not tasks:
        await callback.message.edit_text("🎉 Все активные задания отменены (список пуст).")
    else:
        b = builders.InlineKeyboardBuilder()
        for t in tasks:
            b.button(text=f"❌ {t['text'][:20]}... ({t['full_name']})", callback_data=f"admin_cancel:{t['id']}")
        b.button(text="🔙 Назад", callback_data="back_to_admin")
        b.adjust(1)
        try:
            await callback.message.edit_text("Выберите задание для отмены:", reply_markup=b.as_markup())
        except TelegramBadRequest:
            pass
    await callback.answer("Задание аннулировано.")