from aiogram.utils.keyboard import InlineKeyboardBuilder

def checklist_editor_numbers(items: list, role: str):
    """
    Создает клавиатуру с цифрами для удаления пунктов.
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопки с цифрами для удаления
    for item in items:
        # data format: del_item:ID:ROLE
        builder.button(text=f"🗑 {item['num']}", callback_data=f"del_item:{item['id']}:{role}")
    
    builder.adjust(4) # По 4 цифры в ряд
    
    # Кнопки добавления
    builder.button(text="➕ Утро", callback_data=f"add_item:{role}:morning")
    builder.button(text="➕ Вечер", callback_data=f"add_item:{role}:evening")
    builder.button(text="➕ Общее", callback_data=f"add_item:{role}:common")
    builder.button(text="🔙 К выбору роли", callback_data="settings_checklists")
    
    builder.adjust(4, 3, 1) # Цифры, Добавление, Назад
    return builder.as_markup()

def dynamic_role_select(roles: list, prefix: str):
    """
    Генерирует кнопки ролей из базы данных.
    prefix: 'create_invite' или 'edit_cl'
    """
    builder = InlineKeyboardBuilder()
    for role in roles:
        slug = role['slug']
        name = role['name']
        builder.button(text=f"{name}", callback_data=f"{prefix}:{slug}")
    
    builder.button(text="🔙 Отмена", callback_data="back_to_admin")
    builder.adjust(2)
    return builder.as_markup()

def delete_role_select(roles: list):
    builder = InlineKeyboardBuilder()
    for role in roles:
        if role['slug'] == 'admin': continue
        builder.button(text=f"❌ {role['name']}", callback_data=f"del_role_db:{role['slug']}")
    builder.button(text="🔙 Отмена", callback_data="back_to_admin")
    builder.adjust(1)
    return builder.as_markup()

# --- Старые функции (оставляем, они нужны) ---
def staff_list(users, current_user_id):
    builder = InlineKeyboardBuilder()
    for u in users:
        if not u['is_active']: continue
        text = f"{u['full_name']} — {u['role']} ({u['balance']} 💎)"
        builder.button(text=text, callback_data=f"open_staff:{u['tg_id']}")
    builder.button(text="🔽 Закрыть", callback_data="close_delete_menu")
    builder.adjust(1)
    return builder.as_markup()

def employee_actions(user_id, user_name):
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 KPI и Выплата", callback_data=f"kpi:{user_id}")
    builder.button(text="🔄 Новый период (Сброс)", callback_data=f"reset_stats:{user_id}")
    builder.button(text="💰 Штраф / Премия", callback_data=f"money:{user_id}")
    builder.button(text="❌ Уволить", callback_data=f"fire:{user_id}")
    builder.button(text="🔙 Назад", callback_data="back_to_staff")
    builder.adjust(1)
    return builder.as_markup()

def delete_menu(users, current_user_id):
    builder = InlineKeyboardBuilder()
    for u in users:
        if u['tg_id'] == current_user_id: continue 
        if u['is_active']:
            builder.button(text=f"❌ Удалить: {u['full_name']}", callback_data=f"fire:{u['tg_id']}")
    builder.button(text="🔙 Отмена", callback_data="close_delete_menu")
    builder.adjust(1) 
    return builder.as_markup()

def task_assign_menu(users, current_user_id, active_shifts_ids: list):
    builder = InlineKeyboardBuilder()
    for u in users:
        if u['tg_id'] != current_user_id and u['is_active']:
            status_icon = "🟢" if u['tg_id'] in active_shifts_ids else "💤"
            text = f"{status_icon} {u['full_name']} ({u['role']})"
            builder.button(text=f"{text}", callback_data=f"assign:{u['tg_id']}")
    builder.button(text="❌ Отмена", callback_data="cancel_task")
    builder.adjust(1)
    return builder.as_markup()

def checklist_kb(completed_tasks: list, shift_id: int, tasks_list: list):
    builder = InlineKeyboardBuilder()
    for i, task in enumerate(tasks_list):
        if task in completed_tasks:
            text = f"✅ {task}"
            callback = f"check_off:{i}:{shift_id}"
        else:
            text = f"🟥 {task}"
            callback = f"check_on:{i}:{shift_id}"
        builder.button(text=text, callback_data=callback)
    builder.adjust(1)
    builder.button(text="📤 Отправить отчет админу", callback_data=f"submit_checklist:{shift_id}")
    builder.button(text="🔽 Скрыть", callback_data="close_checklist")
    builder.adjust(1)
    return builder.as_markup()

def active_shifts_menu(shifts):
    builder = InlineKeyboardBuilder()
    for shift in shifts:
        btn_text = f"👤 {shift['full_name']} ({shift.get('shift_type', 'full')})"
        builder.button(text=btn_text, callback_data=f"monitor:{shift['user_id']}")
    builder.button(text="🔄 Обновить", callback_data="refresh_monitor")
    builder.button(text="🔽 Закрыть", callback_data="close_checklist")
    builder.adjust(1)
    return builder.as_markup()

def back_to_monitor():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад к списку", callback_data="refresh_monitor")
    return builder.as_markup()

def reminders_list_menu(reminders: list):
    builder = InlineKeyboardBuilder()
    for r in reminders:
        builder.button(
            text=f"🗑 {r['role']} | {r['interval_hours']}ч | {r['text'][:10]}...", 
            callback_data=f"del_remind:{r['id']}"
        )
    builder.adjust(1)
    builder.button(text="➕ Добавить уведомление", callback_data="add_reminder_start")
    builder.button(text="🔙 В меню", callback_data="back_to_admin")
    builder.adjust(1)
    return builder.as_markup()