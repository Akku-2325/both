import json
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from app.database.repo import users as user_repo
from app.database.repo import shifts as shift_repo
from app.database.repo import tasks as task_repo
from app.database.repo import checklists as check_repo
from app.database.repo import roles as role_repo

from app.services import kpi as kpi_service
from app.keyboards import reply, builders
from app.states import MoneyState, AddStaffState 

router = Router()

# ==========================================
# 1. УПРАВЛЕНИЕ РОЛЯМИ (НОВОЕ)
# ==========================================
@router.message(F.text == "🎭 Роли")
async def roles_menu(message: Message):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    await message.answer("🎭 <b>Управление ролями:</b>", reply_markup=reply.admin_roles_menu())

@router.message(F.text == "➕ Добавить роль")
async def add_role_start(message: Message, state: FSMContext):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    await state.set_state("waiting_role_name")
    await message.answer("✍️ Введите название роли (например: <b>Уборщица</b>):", reply_markup=reply.cancel())

@router.message(StateFilter("waiting_role_name"))
async def add_role_name(message: Message, state: FSMContext):
    name = message.text
    if name == "❌ Отмена":
        await state.clear()
        return await message.answer("Отменено.", reply_markup=reply.admin_main())
        
    await state.update_data(name=name)
    await state.set_state("waiting_role_slug")
    await message.answer("✍️ Введите системный код роли на английском (например: <b>cleaner</b>):")

@router.message(StateFilter("waiting_role_slug"))
async def add_role_slug(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        return await message.answer("Отменено.", reply_markup=reply.admin_main())

    slug = message.text.lower().strip()
    data = await state.get_data()
    
    await role_repo.add_role(slug, data['name'])
    await state.clear()
    await message.answer(f"✅ Роль <b>{data['name']}</b> ({slug}) добавлена!", reply_markup=reply.admin_main())

@router.message(F.text == "❌ Удалить роль")
async def del_role_start(message: Message):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    roles = await role_repo.get_all_roles()
    await message.answer("Какую удалить?", reply_markup=builders.delete_role_select(roles))

@router.callback_query(F.data.startswith("del_role_db:"))
async def del_role_db(callback: CallbackQuery):
    slug = callback.data.split(":")[1]
    await role_repo.delete_role(slug)
    await callback.answer("Роль удалена.")
    await callback.message.delete()
    await callback.message.answer("🗑 Роль удалена.", reply_markup=reply.admin_main())

# ==========================================
# 2. ПРИГЛАШЕНИЯ (INVITES) - НОВОЕ
# ==========================================
@router.message(F.text.in_({"🔗 Создать приглашение", "🔗 Приглашения"}))
async def invite_start(message: Message):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    roles = await role_repo.get_all_roles()
    await message.answer("Для кого создать ссылку?", reply_markup=builders.dynamic_role_select(roles, "create_invite"))

@router.callback_query(F.data.startswith("create_invite:"))
async def create_invite_link(callback: CallbackQuery, bot: Bot):
    role = callback.data.split(":")[1]
    code = await check_repo.create_invite(role)
    
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={code}"
    
    await callback.message.edit_text(
        f"✅ <b>Ссылка для {role} создана!</b>\n"
        f"Нажмите на код ниже, чтобы скопировать:\n\n"
        f"<code>{link}</code>\n\n"
        f"<i>Ссылка одноразовая. Сотрудник перейдет по ней и сам введет свои данные.</i>",
        reply_markup=builders.InlineKeyboardBuilder().button(text="🔙 Назад", callback_data="back_to_admin").as_markup()
    )

# ==========================================
# 3. РЕДАКТОР ЧЕК-ЛИСТОВ (ОБНОВЛЕННЫЙ)
# ==========================================
@router.message(F.text.in_({"⚙️ Настройки", "⚙️ Чек-листы"}))
async def settings_menu(message: Message):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    roles = await role_repo.get_all_roles()
    await message.answer("📝 <b>Чек-листы. Выберите роль:</b>", reply_markup=builders.dynamic_role_select(roles, "edit_cl"))

@router.callback_query(F.data == "settings_checklists")
async def back_to_roles_cl(callback: CallbackQuery):
    roles = await role_repo.get_all_roles()
    await callback.message.edit_text("📝 <b>Выберите роль:</b>", reply_markup=builders.dynamic_role_select(roles, "edit_cl"))

@router.callback_query(F.data.startswith("edit_cl:"))
async def view_checklist_text(callback: CallbackQuery):
    role = callback.data.split(":")[1]
    items = await check_repo.get_all_checklist_items(role)
    
    numbered_items = []
    
    if not items:
        msg = f"📝 <b>Чек-лист: {role}</b>\n\n<i>Список пуст.</i>"
    else:
        text_lines = [f"📝 <b>Чек-лист: {role}</b>\n"]
        count = 1
        for item in items:
            icon = "🌅" if item['shift_type'] == "morning" else "🌇" if item['shift_type'] == "evening" else "🔄"
            text_lines.append(f"<b>{count}.</b> {icon} {item['text']}")
            
            item_dict = dict(item)
            item_dict['num'] = count
            numbered_items.append(item_dict)
            count += 1
            
        msg = "\n".join(text_lines)
        msg += "\n\n👇 <i>Нажмите на цифру, чтобы удалить пункт.</i>"

    await callback.message.edit_text(
        msg,
        reply_markup=builders.checklist_editor_numbers(numbered_items, role)
    )

@router.callback_query(F.data.startswith("del_item:"))
async def delete_checklist_item(callback: CallbackQuery):
    parts = callback.data.split(":")
    item_id = int(parts[1])
    # role = parts[2] - можно использовать для проверки, но view_checklist_text берет из callback.data предыдущего меню
    
    await check_repo.delete_checklist_item(item_id)
    await view_checklist_text(callback)
    await callback.answer("Пункт удален.")

@router.callback_query(F.data.startswith("add_item:"))
async def add_item_start(callback: CallbackQuery, state: FSMContext):
    _, role, shift_type = callback.data.split(":")
    await state.update_data(role=role, shift_type=shift_type)
    await state.set_state("waiting_checklist_text") 
    
    types = {"morning": "Утро", "evening": "Вечер", "common": "Общее"}
    await callback.message.edit_text(
        f"✍️ Введите текст задачи для <b>{role} ({types[shift_type]})</b>:",
        reply_markup=None
    )

@router.message(StateFilter("waiting_checklist_text"))
async def add_item_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    await check_repo.add_checklist_item(data['role'], data['shift_type'], message.text)
    await state.clear()
    await message.answer(f"✅ Добавлено: {message.text}", reply_markup=reply.admin_main())


# ==========================================
# 4. НАПОМИНАНИЯ
# ==========================================
@router.message(F.text == "🔔 Напоминания")
async def reminders_menu(message: Message):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    reminders = await check_repo.get_all_reminders()
    await message.answer(
        "🔔 <b>Активные напоминания:</b>\nБот отправляет их сотрудникам на смене.",
        reply_markup=builders.reminders_list_menu(reminders)
    )

@router.callback_query(F.data == "add_reminder_start")
async def add_remind_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state("remind_role")
    roles = await role_repo.get_all_roles()
    await callback.message.edit_text("Для кого?", reply_markup=builders.dynamic_role_select(roles, "remind_role"))

@router.callback_query(F.data.startswith("remind_role:"))
async def add_remind_role(callback: CallbackQuery, state: FSMContext):
    role = callback.data.split(":")[1]
    await state.update_data(role=role)
    await state.set_state("remind_text")
    await callback.message.edit_text("✍️ Введите текст напоминания:")

@router.message(StateFilter("remind_text"))
async def add_remind_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await state.set_state("remind_interval")
    await message.answer("⏱ Интервал (в часах, просто число):")

@router.message(StateFilter("remind_interval"))
async def add_remind_finish(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("Число!")
    data = await state.get_data()
    await check_repo.add_reminder(data['role'], data['text'], int(message.text))
    await state.clear()
    await message.answer("✅ Напоминание сохранено.", reply_markup=reply.admin_main())

@router.callback_query(F.data.startswith("del_remind:"))
async def delete_remind(callback: CallbackQuery):
    rid = int(callback.data.split(":")[1])
    await check_repo.delete_reminder(rid)
    await callback.answer("Удалено.")
    await reminders_menu(callback.message)


# ==========================================
# 5. СОТРУДНИКИ И МОНИТОРИНГ (КЛАССИКА)
# ==========================================
@router.message(F.text == "🔙 В Главное меню")
async def back_main(message: Message):
    await message.answer("Главное меню", reply_markup=reply.admin_main())

@router.message(F.text == "👥 Сотрудники")
async def list_staff(message: Message):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    users = await user_repo.get_all_users()
    await message.answer("📂 <b>Сотрудники:</b>", reply_markup=builders.staff_list(users, message.from_user.id))

@router.callback_query(F.data.startswith("open_staff:"))
async def open_staff_menu(callback: CallbackQuery):
    tg_id = int(callback.data.split(":")[1])
    user = await user_repo.get_user(tg_id)
    if not user: return await callback.answer("Не найден.")
    
    await callback.message.edit_text(
        f"👤 <b>{user['full_name']}</b>\n💼 {user['role']}\n💎 Баланс: {user['balance']}", 
        reply_markup=builders.employee_actions(user['tg_id'], user['full_name'])
    )

@router.callback_query(F.data == "back_to_staff")
async def back_to_staff_list(callback: CallbackQuery):
    users = await user_repo.get_all_users()
    await callback.message.edit_text("📂 <b>Сотрудники:</b>", reply_markup=builders.staff_list(users, callback.from_user.id))

@router.callback_query(F.data == "back_to_admin")
async def back_admin_inline(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Меню", reply_markup=reply.admin_main())

@router.message(F.text == "👀 Мониторинг")
async def monitor_menu(message: Message):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    shifts = await shift_repo.get_all_active_shifts_data()
    if not shifts: return await message.answer("🤷‍♂️ Смены закрыты.")
    await message.answer("🔎 <b>Выберите сотрудника:</b>", reply_markup=builders.active_shifts_menu(shifts))

@router.callback_query(F.data == "refresh_monitor")
async def refresh_monitor_list(callback: CallbackQuery):
    shifts = await shift_repo.get_all_active_shifts_data()
    if not shifts: return await callback.message.edit_text("🤷‍♂️ Все смены закрыты.", reply_markup=None)
    await callback.message.edit_text("🔎 <b>Выберите сотрудника:</b>", reply_markup=builders.active_shifts_menu(shifts))

@router.callback_query(F.data.startswith("monitor:"))
async def monitor_specific_user(callback: CallbackQuery):
    target_id = int(callback.data.split(":")[1])
    active = await shift_repo.get_active_shift(target_id)
    if not active:
        await callback.answer("Смена закрыта!", show_alert=True)
        return await refresh_monitor_list(callback)
    
    user = await user_repo.get_user(target_id)
    name = user['full_name']
    
    try:
        data = json.loads(active['report']) if active['report'] else {}
        done = [t['title'] for t in data.get('duties', []) if t['done']]
    except: done = []

    tasks_list = await check_repo.get_checklist(active['role'], active['shift_type'])

    visual = "".join([f"✅ {t}\n" if t in done else f"🟥 {t}\n" for t in tasks_list])
    
    total = len(tasks_list)
    completed_count = len(done)
    percent = int((completed_count / total) * 100) if total > 0 else 0
    type_icon = {"morning": "🌅", "evening": "🌇", "full": "📅"}.get(active['shift_type'], "")
    bar_count = percent // 10
    progress_bar = "🟩" * bar_count + "⬜️" * (10 - bar_count)

    text = (
        f"👤 <b>{name}</b> ({active['role']}) {type_icon}\n"
        f"🕒 Нач: {active['started_at']}\n"
        f"📊 {completed_count}/{total} ({percent}%)\n"
        f"{progress_bar}\n\n"
        f"{visual}"
    )
    await callback.message.edit_text(text, reply_markup=builders.back_to_monitor())

# ==========================================
# 6. KPI И ДЕНЬГИ
# ==========================================
@router.callback_query(F.data.startswith("kpi:"))
async def show_kpi_stats(callback: CallbackQuery):
    tg_id = int(callback.data.split(":")[1])
    user = await user_repo.get_user(tg_id)
    
    stats = await kpi_service.calculate_kpi(tg_id)
    
    emoji = "✅" if stats['is_eligible'] else "⚠️"
    status_text = "<b>БОНУС ПОЛОЖЕН</b>" if stats['is_eligible'] else "<b>Меньше 90% качества!</b>"
    
    text = (
        f"📊 <b>KPI Сотрудника: {user['full_name']}</b>\n"
        f"<i>(Анализ чек-листов за период)</i>\n\n"
        f"📅 <b>Смен (X):</b> {stats['shifts_x']}\n"
        f"☑️ <b>Ср. задач в день (Y):</b> {stats['tasks_y_avg']}\n"
        f"🚀 <b>KPI (X * Y):</b> {stats['activity_score']} (всего галочек)\n\n"
        f"📈 <b>Общее качество:</b> {stats['efficiency_percent']}%\n"
        f"🎯 <b>План:</b> 90%\n"
        f"{emoji} {status_text}\n\n"
        f"💰 <b>Накоплено баллов:</b> {user['balance']}"
    )
    
    kb = builders.InlineKeyboardBuilder()
    kb.button(text="💸 Выплатить и обнулить", callback_data=f"pay_bonus:{tg_id}")
    kb.button(text="🔙 Назад", callback_data=f"open_staff:{tg_id}")
    kb.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("pay_bonus:"))
async def pay_bonus_handler(callback: CallbackQuery):
    tg_id = int(callback.data.split(":")[1])
    user = await user_repo.get_user(tg_id)
    
    amount = user['balance']
    if amount <= 0:
        return await callback.answer("Баланс уже пуст!", show_alert=True)
        
    await task_repo.reset_balance(tg_id)
    
    await callback.answer(f"✅ Выплачено {amount} баллов!", show_alert=True)
    await show_kpi_stats(callback)
    
    try:
        await callback.bot.send_message(tg_id, f"🥳 <b>Поздравляем!</b>\nВам выплачен бонус: {amount} баллов.\nБаланс обнулен.")
    except: pass

@router.callback_query(F.data.startswith("reset_stats:"))
async def ask_reset_stats(callback: CallbackQuery):
    tg_id = int(callback.data.split(":")[1])
    
    builder = builders.InlineKeyboardBuilder()
    builder.button(text="✅ Да, сбросить статистику", callback_data=f"confirm_reset:{tg_id}")
    builder.button(text="❌ Нет, отмена", callback_data=f"open_staff:{tg_id}")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "⚠️ <b>Вы уверены?</b>\n\n"
        "Это обнулит счетчики:\n"
        "— Количество смен (X)\n"
        "— Выполненные задачи (Y)\n"
        "— Процент качества\n\n"
        "<i>(Баланс денег останется прежним, сбросится только статистика для KPI. Например, начало нового месяца.)</i>",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("confirm_reset:"))
async def confirm_reset_stats(callback: CallbackQuery):
    tg_id = int(callback.data.split(":")[1])
    await user_repo.reset_user_kpi_date(tg_id)
    await callback.answer("✅ Статистика обнулена! Начался новый период.", show_alert=True)
    await open_staff_menu(callback)

@router.callback_query(F.data.startswith("money:"))
async def money_start(callback: CallbackQuery, state: FSMContext):
    tg_id = int(callback.data.split(":")[1])
    await state.update_data(target_id=tg_id)
    
    await state.set_state(MoneyState.waiting_for_amount)
    await callback.message.answer(
        "💰 <b>Введите сумму баллов:</b>\n\n"
        "➕ Если хотите дать премию: напишите просто число (например: <code>500</code>)\n"
        "➖ Если хотите оштрафовать: напишите число с минусом (например: <code>-500</code>)",
        reply_markup=reply.cancel()
    )
    await callback.answer()

@router.message(MoneyState.waiting_for_amount)
async def money_amount_handler(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        return await message.answer("Отменено.", reply_markup=reply.admin_main())

    try:
        amount = int(message.text)
        await state.update_data(amount=amount)
        await state.set_state(MoneyState.waiting_for_reason)
        
        action = "премии" if amount > 0 else "штрафа"
        await message.answer(f"✍️ <b>Напишите причину {action}:</b>\n(Например: <i>Опоздание на 15 мин</i> или <i>Отличная работа</i>)")
    except ValueError:
        await message.answer("❌ Введите целое число (например: 100 или -100).")

@router.message(MoneyState.waiting_for_reason)
async def money_reason_handler(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        return await message.answer("Отменено.", reply_markup=reply.admin_main())

    data = await state.get_data()
    target_id = data['target_id']
    amount = data['amount']
    reason = message.text
    
    await task_repo.add_bonus(target_id, amount)
    
    user = await user_repo.get_user(target_id)
    
    await message.answer(
        f"✅ <b>Готово!</b>\n"
        f"👤 Сотрудник: {user['full_name']}\n"
        f"💰 Сумма: {amount:+}\n"
        f"📝 Причина: {reason}\n"
        f"💎 Теперь баланс: {user['balance']}",
        reply_markup=reply.admin_main()
    )
    
    action_emoji = "🎁" if amount > 0 else "📉"
    action_title = "ПРЕМИЯ" if amount > 0 else "ШТРАФ"
    
    try:
        await message.bot.send_message(
            target_id,
            f"{action_emoji} <b>ВНИМАНИЕ: {action_title}!</b>\n\n"
            f"💰 <b>Изменение баланса:</b> {amount:+} баллов\n"
            f"📝 <b>Причина:</b> {reason}\n\n"
            f"💳 <b>Ваш текущий баланс:</b> {user['balance']}"
        )
    except:
        pass 

    await state.clear()

# ==========================================
# 7. РУЧНОЕ УДАЛЕНИЕ И ДОБАВЛЕНИЕ (ОСТАВЛЕНО)
# ==========================================
@router.message(F.text == "🗑 Удалить сотрудника")
async def delete_staff_start(message: Message):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    users = await user_repo.get_all_users()
    await message.answer("🗑 <b>Кого удалить?</b>", reply_markup=builders.delete_menu(users, message.from_user.id))

@router.callback_query(F.data.startswith("fire:"))
async def ask_fire_staff(callback: CallbackQuery):
    tg_id = int(callback.data.split(":")[1])
    user = await user_repo.get_user(tg_id)
    
    if not user:
        return await callback.answer("Сотрудник не найден.", show_alert=True)

    builder = builders.InlineKeyboardBuilder()
    builder.button(text="☢️ ДА, удалить полностью", callback_data=f"confirm_fire:{tg_id}")
    builder.button(text="🔙 Нет, отмена", callback_data=f"open_staff:{tg_id}")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"⚠️ <b>ВЫ УВЕРЕНЫ?</b>\n\n"
        f"Вы собираетесь удалить сотрудника: <b>{user['full_name']}</b>.\n\n"
        f"❗️ <b>Это удалит ВСЮ информацию:</b>\n"
        f"— Историю его смен\n"
        f"— Выполненные задачи\n"
        f"— Накопленный баланс\n\n"
        f"<i>Это действие нельзя отменить.</i>",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("confirm_fire:"))
async def confirm_fire_staff(callback: CallbackQuery):
    tg_id = int(callback.data.split(":")[1])
    await user_repo.fully_delete_user(tg_id)
    await callback.answer("✅ Сотрудник и все его данные удалены.", show_alert=True)
    
    users = await user_repo.get_all_users()
    await callback.message.edit_text("📂 <b>Сотрудники:</b>", reply_markup=builders.staff_list(users, callback.from_user.id))

@router.callback_query(F.data == "close_delete_menu")
async def close_menu(c: CallbackQuery): await c.message.delete()
@router.callback_query(F.data == "ignore")
async def ignore(c: CallbackQuery): await c.answer()

@router.message(StateFilter(AddStaffState), F.text == "❌ Отмена")
async def cancel_admin_global(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=reply.admin_main())

@router.message(F.text == "➕ Добавить сотрудника")
async def add_start(message: Message, state: FSMContext):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    await state.set_state(AddStaffState.waiting_for_id)
    await message.answer("1️⃣ Telegram ID сотрудника:", reply_markup=reply.cancel())

@router.message(AddStaffState.waiting_for_id)
async def add_id(message: Message, state: FSMContext):
    if not message.text: return
    if message.text.isdigit():
        tg_id = int(message.text)
        existing = await user_repo.get_user(tg_id)
        if existing and existing['is_active']:
            return await message.answer(f"⛔ Сотрудник {existing['full_name']} уже работает.", reply_markup=reply.cancel())
        await state.update_data(tg_id=tg_id)
        await state.set_state(AddStaffState.waiting_for_name)
        await message.answer("2️⃣ Имя:")
    else:
        await message.answer("❌ Нужны цифры.")

@router.message(AddStaffState.waiting_for_name)
async def add_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddStaffState.waiting_for_role)
    await message.answer("3️⃣ Должность:", reply_markup=reply.roles())

@router.message(AddStaffState.waiting_for_role)
async def add_role(message: Message, state: FSMContext):
    # Разрешаем любые роли для обратной совместимости, или можно брать из БД
    await state.update_data(role=message.text)
    await state.set_state(AddStaffState.waiting_for_pin)
    await message.answer("4️⃣ PIN-код (4 цифры):", reply_markup=reply.cancel())

@router.message(AddStaffState.waiting_for_pin)
async def add_pin(message: Message, state: FSMContext):
    if not message.text.isdigit() or len(message.text) != 4:
        return await message.answer("❌ PIN — 4 цифры.")
    data = await state.get_data()
    await user_repo.add_user(data['tg_id'], data['name'], data['role'], message.text)
    await state.clear()
    await message.answer(f"✅ Сотрудник {data['name']} добавлен!", reply_markup=reply.admin_main())

# Задания в этом файле обрабатывать не надо, они в tasks.py
# Здесь только редирект если нажали кнопку
@router.message(F.text == "📝 Задания")
async def tasks_menu_proxy(message: Message):
    # Просто подскажем, хотя обработчик в tasks.py перехватит, если там F.text совпадает
    # Если здесь будет этот хендлер, он может перехватить раньше.
    # Поэтому лучше ничего не делать, tasks.py справится, если роутеры подключены.
    pass