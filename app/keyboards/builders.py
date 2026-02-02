from aiogram.utils.keyboard import InlineKeyboardBuilder

def staff_list(users, current_user_id, roles_map):
    builder = InlineKeyboardBuilder()
    for u in users:
        if not u['is_active']: continue
        r_name = roles_map.get(u['role'], u['role'])
        builder.button(text=f"{u['full_name']} — {r_name}", callback_data=f"open_staff:{u['tg_id']}")
    builder.button(text="🔽 Закрыть", callback_data="close_checklist")
    builder.adjust(1)
    return builder.as_markup()

def employee_actions(user_id, user_name):
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 KPI и Выплата", callback_data=f"kpi:{user_id}")
    builder.button(text="🔄 Новый период (Сброс)", callback_data=f"reset_stats:{user_id}")
    builder.button(text="💰 Штраф / Премия", callback_data=f"money:{user_id}")
    builder.button(text="❌ Удалить сотрудника", callback_data=f"fire:{user_id}")
    builder.button(text="🔙 Назад", callback_data="back_to_staff")
    builder.adjust(1)
    return builder.as_markup()

def active_shifts_menu(shifts, roles_map=None):
    if roles_map is None: roles_map = {}
    builder = InlineKeyboardBuilder()
    for shift in shifts:
        r_name = roles_map.get(shift['role'], shift['role'])
        builder.button(text=f"👤 {shift['full_name']} ({r_name})", callback_data=f"monitor:{shift['user_id']}")
    builder.button(text="🔄 Обновить", callback_data="refresh_monitor")
    builder.button(text="🔽 Закрыть", callback_data="close_checklist")
    builder.adjust(1)
    return builder.as_markup()

def dynamic_role_select(roles: list, prefix: str, show_admin: bool = False):
    builder = InlineKeyboardBuilder()
    for role in roles:
        if role['slug'] == 'admin' and not show_admin: continue
        builder.button(text=f"{role['name']}", callback_data=f"{prefix}:{role['slug']}")
    builder.button(text="🔙 Назад", callback_data="back_to_admin")
    builder.adjust(2)
    return builder.as_markup()

def checklist_categories(role_slug):
    builder = InlineKeyboardBuilder()
    builder.button(text="🌅 Утро", callback_data=f"open_cat:{role_slug}:morning")
    builder.button(text="🔄 Общее", callback_data=f"open_cat:{role_slug}:common")
    builder.button(text="🌇 Вечер", callback_data=f"open_cat:{role_slug}:evening")
    builder.button(text="🔙 Назад", callback_data="settings_checklists")
    builder.adjust(1)
    return builder.as_markup()

def checklist_items_edit(items: list, role_slug: str, shift_type: str, mode: str = "view", selected_ids: list = None, page: int = 0):
    if selected_ids is None: selected_ids = []
    ITEMS_PER_PAGE = 8
    builder = InlineKeyboardBuilder()

    if mode == "view":
        builder.button(text="➕ Добавить задачу", callback_data=f"add_item:{role_slug}:{shift_type}")
        builder.button(text="🗑 Удалить задачи", callback_data=f"mode_del:{role_slug}:{shift_type}")
        builder.button(text="🔙 Назад", callback_data=f"edit_cl:{role_slug}")
        builder.button(text="🏠 Закончить", callback_data="back_to_admin")
        builder.adjust(1)
        return builder.as_markup()
        
    elif mode == "delete":
        total_items = len(items)
        start_index = page * ITEMS_PER_PAGE
        end_index = start_index + ITEMS_PER_PAGE
        page_items = items[start_index:end_index]
        
        for item in page_items:
            icon = "✅" if item['id'] in selected_ids else "⬜"
            short_text = item['text'][:15] + ".." if len(item['text']) > 15 else item['text']
            builder.button(text=f"{icon} {short_text}", callback_data=f"toggle_sel:{item['id']}:{role_slug}:{shift_type}")
        builder.adjust(2)

        nav_builder = InlineKeyboardBuilder()
        total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        
        if total_pages > 1:
            if page > 0: nav_builder.button(text="⬅️", callback_data=f"cl_page:{page-1}:{role_slug}:{shift_type}")
            else: nav_builder.button(text="▫️", callback_data="noop")
            nav_builder.button(text=f"{page + 1}/{total_pages}", callback_data="noop")
            if end_index < total_items: nav_builder.button(text="➡️", callback_data=f"cl_page:{page+1}:{role_slug}:{shift_type}")
            else: nav_builder.button(text="▫️", callback_data="noop")
            nav_builder.adjust(3)
            builder.attach(nav_builder)

        control = InlineKeyboardBuilder()
        if selected_ids: control.button(text=f"🗑 Удалить ({len(selected_ids)})", callback_data=f"confirm_del:{role_slug}:{shift_type}")
        control.button(text="🔙 Отмена", callback_data=f"open_cat:{role_slug}:{shift_type}")
        control.adjust(1)
        builder.attach(control)
    return builder.as_markup()

def task_assign_menu(users, current_user_id, active_ids, roles_map):
    builder = InlineKeyboardBuilder()
    for u in users:
        if u['tg_id'] == current_user_id or not u['is_active']: continue
        status = "🟢" if u['tg_id'] in active_ids else "💤"
        r_name = roles_map.get(u['role'], u['role'])
        builder.button(text=f"{status} {u['full_name']} ({r_name})", callback_data=f"assign:{u['tg_id']}")
    builder.button(text="❌ Отмена", callback_data="cancel_task")
    builder.adjust(1)
    return builder.as_markup()

def reminders_list_menu(reminders: list, roles_map: dict):
    builder = InlineKeyboardBuilder()
    for r in reminders:
        r_name = roles_map.get(r['role'], r['role'])
        builder.button(text=f"❌ {r_name}: {r['text'][:15]}...", callback_data=f"del_remind:{r['id']}")
    builder.button(text="➕ Добавить", callback_data="add_reminder_start")
    builder.button(text="🔙 Назад", callback_data="back_to_admin")
    builder.adjust(1)
    return builder.as_markup()

def back_to_monitor():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 К списку", callback_data="refresh_monitor")
    return builder.as_markup()

def delete_role_select(roles: list):
    builder = InlineKeyboardBuilder()
    for role in roles:
        if role['slug'] == 'admin': continue
        builder.button(text=f"🗑 {role['name']}", callback_data=f"del_role_db:{role['slug']}")
    builder.button(text="🔙 Назад", callback_data="back_to_admin")
    builder.adjust(1)
    return builder.as_markup()

def confirm_delete_role_menu(role_slug):
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Да, удалить", callback_data=f"confirm_del_role:{role_slug}")
    builder.button(text="🔙 Нет, отмена", callback_data="cancel_del_role")
    builder.adjust(1)
    return builder.as_markup()

def checklist_kb(status_list: list, shift_id: int, tasks_list: list):
    builder = InlineKeyboardBuilder()
    for i, task in enumerate(tasks_list):
        is_done = status_list[i] if i < len(status_list) else False
        
        icon = "🟥"
        if is_done: icon = "✅"
        elif task.get('item_type') == 'photo': icon = "📸"
        elif task.get('item_type') == 'video': icon = "🎥"
        
        text = f"{icon} {task['text']}"
        callback_action = "check_off" if is_done else "check_on"
        builder.button(text=text, callback_data=f"{callback_action}:{i}:{shift_id}")

    builder.adjust(1)
    control_builder = InlineKeyboardBuilder()
    control_builder.button(text="📤 Отправить отчет", callback_data=f"submit_checklist:{shift_id}")
    control_builder.button(text="🔽 Скрыть", callback_data="close_checklist")
    control_builder.adjust(1)
    builder.attach(control_builder)
    return builder.as_markup()