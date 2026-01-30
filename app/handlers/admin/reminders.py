from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from app.database.repo import users as user_repo, checklists as check_repo, roles as role_repo
from app.keyboards import builders, reply
from app.states.states import ReminderState

router = Router()

@router.message(F.text == "🔔 Напоминания")
async def reminders_menu(message: Message, restaurant_id: int):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    
    reminders = await check_repo.get_all_reminders(restaurant_id)
    roles_map = await role_repo.get_roles_map(restaurant_id)
    
    if not reminders:
        return await message.answer("🔔 <b>Список напоминаний пуст.</b>", reply_markup=builders.reminders_list_menu([], roles_map))

    text = "🔔 <b>Активные напоминания:</b>\n"
    for r in reminders:
        r_name = roles_map.get(r['role'], r['role'])
        text += f"• <b>{r_name}</b>: {r['text']} (каждые {r['interval_hours']} мин)\n"
        
    await message.answer(text, reply_markup=builders.reminders_list_menu(reminders, roles_map))

@router.callback_query(F.data == "add_reminder_start")
async def add_remind_start(callback: CallbackQuery, state: FSMContext, restaurant_id: int):
    await state.set_state(ReminderState.remind_role)
    roles = await role_repo.get_all_roles(restaurant_id)
    await callback.message.edit_text("Для какой роли создать напоминание?", reply_markup=builders.dynamic_role_select(roles, "remind_role"))

@router.callback_query(F.data.startswith("remind_role:"))
async def add_remind_role(callback: CallbackQuery, state: FSMContext):
    await state.update_data(role=callback.data.split(":")[1])
    await state.set_state(ReminderState.remind_text)
    await callback.message.edit_text("✍️ Введите текст напоминания:")

@router.message(ReminderState.remind_text)
async def add_remind_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await state.set_state(ReminderState.remind_interval)
    await message.answer("⏱ Интервал повторения в <b>минутах</b> (например, 60 для часа):")

@router.message(ReminderState.remind_interval)
async def add_remind_finish(message: Message, state: FSMContext, restaurant_id: int):
    if not message.text.isdigit(): return await message.answer("❌ Введите целое число минут!")
    data = await state.get_data()
    await check_repo.add_reminder(restaurant_id, data['role'], data['text'], int(message.text))
    await state.clear()
    await message.answer("✅ Периодическое напоминание сохранено.", reply_markup=reply.admin_main())

@router.callback_query(F.data.startswith("del_remind:"))
async def delete_remind(callback: CallbackQuery, restaurant_id: int):
    rem_id = int(callback.data.split(":")[1])
    await check_repo.delete_reminder(rem_id, restaurant_id)
    
    reminders = await check_repo.get_all_reminders(restaurant_id)
    roles_map = await role_repo.get_roles_map(restaurant_id)
    
    if not reminders:
        text = "🔔 <b>Список напоминаний пуст.</b>"
    else:
        text = "🔔 <b>Активные напоминания:</b>\n"
        for r in reminders:
            r_name = roles_map.get(r['role'], r['role'])
            text += f"• <b>{r_name}</b>: {r['text']} (каждые {r['interval_hours']} мин)\n"
    
    try:
        await callback.message.edit_text(text, reply_markup=builders.reminders_list_menu(reminders, roles_map))
    except TelegramBadRequest:
        await callback.answer("Уже обновлено")
    
    await callback.answer("Удалено.")