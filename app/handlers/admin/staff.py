import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from app.database.repo import users as user_repo, tasks as task_repo, roles as role_repo
from app.database.repo import saas as saas_repo
from app.services import kpi as kpi_service
from app.keyboards import reply, builders
from app.states.states import MoneyState

router = Router()

@router.message(F.text == "👥 Сотрудники")
async def list_staff(message: Message, restaurant_id: int):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    users = await user_repo.get_all_users(restaurant_id)
    roles_map = await role_repo.get_roles_map(restaurant_id)
    await message.answer("📂 <b>Сотрудники:</b>", reply_markup=builders.staff_list(users, message.from_user.id, roles_map))

@router.callback_query(F.data.startswith("open_staff:"))
async def open_staff_menu(callback: CallbackQuery, restaurant_id: int):
    tg_id = int(callback.data.split(":")[1])
    user = await user_repo.get_user(tg_id, restaurant_id)
    if not user: return await callback.answer("Сотрудник не найден.")
    
    roles_map = await role_repo.get_roles_map(restaurant_id)
    r_name = roles_map.get(user['role'], user['role'])
    
    await callback.message.edit_text(
        f"👤 <b>{user['full_name']}</b>\n"
        f"💼 Должность: {r_name}\n"
        f"💎 Баланс: {user['balance']} баллов", 
        reply_markup=builders.employee_actions(user['tg_id'], user['full_name'])
    )

@router.callback_query(F.data == "back_to_staff")
async def back_to_staff_list(callback: CallbackQuery, restaurant_id: int):
    users = await user_repo.get_all_users(restaurant_id)
    roles_map = await role_repo.get_roles_map(restaurant_id)
    await callback.message.edit_text("📂 <b>Сотрудники:</b>", reply_markup=builders.staff_list(users, callback.from_user.id, roles_map))

@router.callback_query(F.data.startswith("kpi:"))
async def show_kpi_stats(callback: CallbackQuery, restaurant_id: int):
    tg_id = int(callback.data.split(":")[1])
    user = await user_repo.get_user(tg_id, restaurant_id)
    roles_map = await role_repo.get_roles_map(restaurant_id)
    r_name = roles_map.get(user['role'], user['role'])
    
    stats = await kpi_service.calculate_kpi(tg_id, restaurant_id)
    emoji = "✅" if stats['is_eligible'] else "⚠️"
    status_text = "БОНУС ПОЛОЖЕН" if stats['is_eligible'] else "НИЗКОЕ КАЧЕСТВО"
    
    text = (
        f"📊 <b>KPI Сотрудника: {user['full_name']}</b> ({r_name})\n\n"
        f"📅 <b>Смен (X):</b> {stats['shifts_x']}\n"
        f"☑️ <b>Ср. задач (Y):</b> {stats['tasks_y_avg']}\n"
        f"🚀 <b>Коэф. активности:</b> {stats['activity_score']}\n"
        f"📈 <b>Качество:</b> {stats['efficiency_percent']}%\n\n"
        f"{emoji} <b>{status_text}</b>\n"
        f"💰 <b>Текущий баланс:</b> {user['balance']}"
    )
    
    kb = builders.InlineKeyboardBuilder()
    kb.button(text="💸 Выплатить и обнулить", callback_data=f"pay_bonus:{tg_id}")
    kb.button(text="🔙 Назад", callback_data=f"open_staff:{tg_id}")
    kb.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("pay_bonus:"))
async def pay_bonus_handler(callback: CallbackQuery, restaurant_id: int):
    tg_id = int(callback.data.split(":")[1])
    user = await user_repo.get_user(tg_id, restaurant_id)
    amount = user['balance']
    
    if amount <= 0:
        return await callback.answer("Баланс уже пуст!", show_alert=True)
        
    await task_repo.reset_balance(tg_id, restaurant_id)
    await callback.answer(f"✅ Выплачено {amount} баллов!", show_alert=True)
    
    user = await user_repo.get_user(tg_id, restaurant_id)
    roles_map = await role_repo.get_roles_map(restaurant_id)
    r_name = roles_map.get(user['role'], user['role'])
    stats = await kpi_service.calculate_kpi(tg_id, restaurant_id)
    emoji = "✅" if stats['is_eligible'] else "⚠️"
    status_text = "БОНУС ПОЛОЖЕН" if stats['is_eligible'] else "НИЗКОЕ КАЧЕСТВО"
    
    text = (
        f"📊 <b>KPI Сотрудника: {user['full_name']}</b> ({r_name})\n\n"
        f"📅 <b>Смен (X):</b> {stats['shifts_x']}\n"
        f"☑️ <b>Ср. задач (Y):</b> {stats['tasks_y_avg']}\n"
        f"🚀 <b>Коэф. активности:</b> {stats['activity_score']}\n"
        f"📈 <b>Качество:</b> {stats['efficiency_percent']}%\n\n"
        f"{emoji} <b>{status_text}</b>\n"
        f"💰 <b>Текущий баланс:</b> {user['balance']}" 
    )
    
    kb = builders.InlineKeyboardBuilder()
    kb.button(text="💸 Выплатить и обнулить", callback_data=f"pay_bonus:{tg_id}")
    kb.button(text="🔙 Назад", callback_data=f"open_staff:{tg_id}")
    kb.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    
    try:
        await callback.bot.send_message(tg_id, f"🥳 <b>Вам выплачен бонус: {amount} баллов!</b>\nБаланс обнулен.")
    except: pass

@router.callback_query(F.data.startswith("reset_stats:"))
async def ask_reset_stats(callback: CallbackQuery):
    tg_id = int(callback.data.split(":")[1])
    
    builder = builders.InlineKeyboardBuilder()
    builder.button(text="✅ Да, сбросить", callback_data=f"confirm_reset:{tg_id}")
    builder.button(text="🔙 Отмена", callback_data=f"open_staff:{tg_id}")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "⚠️ <b>Начать новый период?</b>\n\n"
        "Это обнулит счетчики смен и KPI, чтобы начать месяц заново.\n"
        "Баланс денег останется.",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("confirm_reset:"))
async def confirm_reset_stats(callback: CallbackQuery, restaurant_id: int):
    tg_id = int(callback.data.split(":")[1])
    await user_repo.reset_user_kpi_date(tg_id, restaurant_id)
    await callback.answer("✅ Новый период начат.", show_alert=True)
    await open_staff_menu(callback, restaurant_id)

@router.callback_query(F.data.startswith("fire:"))
async def ask_fire_staff(callback: CallbackQuery, restaurant_id: int):
    tg_id = int(callback.data.split(":")[1])
    
    restaurant_info = await saas_repo.get_restaurant_info(restaurant_id)
    
    if restaurant_info and restaurant_info['owner_tg_id'] == tg_id:
        return await callback.answer("⛔ Нельзя удалить Владельца кофейни!", show_alert=True)
        
    if tg_id == callback.from_user.id:
        return await callback.answer("⛔ Вы не можете удалить сами себя. Просто выйдите из аккаунта.", show_alert=True)

    user = await user_repo.get_user(tg_id, restaurant_id)
    
    builder = builders.InlineKeyboardBuilder()
    builder.button(text="🗑 Да, удалить", callback_data=f"confirm_fire:{tg_id}")
    builder.button(text="🔙 Нет, ошибка", callback_data=f"open_staff:{tg_id}")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"⚠️ <b>ВЫ УВЕРЕНЫ?</b>\n\n"
        f"Вы собираетесь удалить сотрудника: <b>{user['full_name']}</b>.\n"
        f"Это действие необратимо. Удалится вся история и баланс.",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("confirm_fire:"))
async def confirm_fire_staff(callback: CallbackQuery, restaurant_id: int):
    tg_id = int(callback.data.split(":")[1])
    await user_repo.fully_delete_user(tg_id, restaurant_id)
    await callback.answer("✅ Сотрудник удален.", show_alert=True)
    await back_to_staff_list(callback, restaurant_id)

@router.callback_query(F.data.startswith("money:"))
async def money_start(callback: CallbackQuery, state: FSMContext):
    tg_id = int(callback.data.split(":")[1])
    await state.update_data(target_id=tg_id)
    
    await state.set_state(MoneyState.waiting_for_amount)
    await callback.message.answer(
        "💰 <b>Введите сумму баллов:</b>\n\n"
        "Пример: <code>500</code> (премия) или <code>-500</code> (штраф).", 
        reply_markup=reply.cancel()
    )
    await callback.answer()

@router.message(StateFilter(MoneyState), F.text == "❌ Отмена")
async def cancel_money_state(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=reply.admin_main())

@router.message(MoneyState.waiting_for_amount)
async def money_amount_handler(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        await state.update_data(amount=amount)
        await state.set_state(MoneyState.waiting_for_reason)
        
        action = "ПРЕМИИ" if amount > 0 else "ШТРАФА"
        await message.answer(f"✍️ <b>Напишите причину {action}:</b>")
    except ValueError:
        await message.answer("❌ Нужно ввести целое число (например: 100). Попробуйте еще раз.")

@router.message(MoneyState.waiting_for_reason)
async def money_reason_handler(message: Message, state: FSMContext, restaurant_id: int):
    data = await state.get_data()
    target_id = data['target_id']
    amount = data['amount']
    reason = message.text
    
    await task_repo.add_bonus(target_id, restaurant_id, amount)
    user = await user_repo.get_user(target_id, restaurant_id)
    
    await message.answer(
        f"✅ <b>Баланс изменен!</b>\n"
        f"👤 Сотрудник: {user['full_name']}\n"
        f"💰 Сумма: {amount:+}\n"
        f"📝 Причина: {reason}\n"
        f"💎 Итог: {user['balance']}",
        reply_markup=reply.admin_main()
    )
    
    emoji = "🎁" if amount > 0 else "📉"
    try:
        await message.bot.send_message(
            target_id,
            f"{emoji} <b>ИЗМЕНЕНИЕ БАЛАНСА: {amount:+}</b>\n"
            f"📝 Причина: {reason}\n"
            f"💳 Ваш баланс: {user['balance']}"
        )
    except: pass
    
    await state.clear()