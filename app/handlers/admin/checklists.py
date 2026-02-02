from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from app.database.repo import users as user_repo, checklists as check_repo, roles as role_repo
from app.keyboards import reply, builders
from app.states.states import ChecklistState

router = Router()

@router.message(F.text.in_({"⚙️ Настройки", "⚙️ Чек-листы"}))
async def settings_menu(message: Message, restaurant_id: int):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    roles = await role_repo.get_all_roles(restaurant_id)
    await message.answer("📝 <b>Редактор чек-листов. Выберите роль:</b>", reply_markup=builders.dynamic_role_select(roles, "edit_cl"))

@router.callback_query(F.data == "settings_checklists")
async def back_to_roles_cl(callback: CallbackQuery, restaurant_id: int):
    roles = await role_repo.get_all_roles(restaurant_id)
    await callback.message.edit_text("📝 <b>Выберите роль:</b>", reply_markup=builders.dynamic_role_select(roles, "edit_cl"))

@router.callback_query(F.data.startswith("edit_cl:"))
async def view_checklist_categories(callback: CallbackQuery, restaurant_id: int):
    role_slug = callback.data.split(":")[1]
    roles_map = await role_repo.get_roles_map(restaurant_id)
    role_name = roles_map.get(role_slug, role_slug)
    
    await callback.message.edit_text(
        f"📂 <b>Настройка: {role_name}</b>\n"
        f"Выберите категорию:",
        reply_markup=builders.checklist_categories(role_slug)
    )

@router.callback_query(F.data.startswith("open_cat:"))
async def view_checklist_items(callback: CallbackQuery, state: FSMContext, restaurant_id: int):
    await state.update_data(selected_ids=[], current_page=0)
    parts = callback.data.split(":")
    role_slug = parts[1]
    shift_type = parts[2]
    await render_checklist_items(callback, restaurant_id, role_slug, shift_type, mode="view")

@router.callback_query(F.data.startswith("mode_del:"))
async def enable_delete_mode(callback: CallbackQuery, state: FSMContext, restaurant_id: int):
    parts = callback.data.split(":")
    role_slug = parts[1]
    shift_type = parts[2]
    await state.update_data(selected_ids=[], current_page=0)
    await render_checklist_items(callback, restaurant_id, role_slug, shift_type, mode="delete", state=state)

@router.callback_query(F.data.startswith("cl_page:"))
async def change_page(callback: CallbackQuery, state: FSMContext, restaurant_id: int):
    parts = callback.data.split(":")
    new_page = int(parts[1])
    role_slug = parts[2]
    shift_type = parts[3]
    
    await state.update_data(current_page=new_page)
    await render_checklist_items(callback, restaurant_id, role_slug, shift_type, mode="delete", state=state)

@router.callback_query(F.data.startswith("toggle_sel:"))
async def toggle_selection(callback: CallbackQuery, state: FSMContext, restaurant_id: int):
    parts = callback.data.split(":")
    item_id = int(parts[1])
    role_slug = parts[2]
    shift_type = parts[3]
    
    data = await state.get_data()
    selected = data.get("selected_ids", [])
    
    if item_id in selected:
        selected.remove(item_id)
    else:
        selected.append(item_id)
        
    await state.update_data(selected_ids=selected)
    await render_checklist_items(callback, restaurant_id, role_slug, shift_type, mode="delete", state=state)

@router.callback_query(F.data.startswith("confirm_del:"))
async def confirm_delete_selected(callback: CallbackQuery, state: FSMContext, restaurant_id: int):
    parts = callback.data.split(":")
    role_slug = parts[1]
    shift_type = parts[2]
    
    data = await state.get_data()
    selected = data.get("selected_ids", [])
    
    if selected:
        for item_id in selected:
            await check_repo.delete_checklist_item(item_id, restaurant_id)
        await callback.answer(f"🗑 Удалено задач: {len(selected)}")
    
    await state.update_data(selected_ids=[], current_page=0)
    await render_checklist_items(callback, restaurant_id, role_slug, shift_type, mode="view")

@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer()

async def render_checklist_items(callback: CallbackQuery, restaurant_id: int, role_slug: str, shift_type: str, mode: str, state: FSMContext = None):
    items = await check_repo.get_items_by_type(restaurant_id, role_slug, shift_type)
    roles_map = await role_repo.get_roles_map(restaurant_id)
    role_name = roles_map.get(role_slug, role_slug)
    
    types_rus = {"morning": "УТРО 🌅", "common": "ОБЩЕЕ 🔄", "evening": "ВЕЧЕР 🌇"}
    type_name = types_rus.get(shift_type, shift_type)
    
    if mode == "delete" and state:
        text = (
            f"🗑 <b>УДАЛЕНИЕ ЗАДАЧ</b>\n"
            f"Роль: <b>{role_name}</b> ({type_name})\n\n"
            f"👇 <i>Отмечайте задачи галочками, затем нажмите «Удалить».</i>"
        )
    else:
        text_lines = [f"📝 <b>{role_name} — {type_name}</b>\n"]
        if not items:
            text_lines.append("<i>Список пуст.</i>")
        else:
            for i, it in enumerate(items, 1):
                type_icon = {"simple": "", "photo": "📸 ", "video": "🎥 "}.get(it.get('item_type', 'simple'), "")
                text_lines.append(f"<b>{i}.</b> {type_icon}{it['text']}")
        text_lines.append("\n✅ <i>Это список задач. Нажмите «Добавить» или «Удалить».</i>")
        text = "\n".join(text_lines)

    selected_ids = []
    current_page = 0
    if state:
        data = await state.get_data()
        selected_ids = data.get("selected_ids", [])
        current_page = data.get("current_page", 0)

    try:
        await callback.message.edit_text(
            text,
            reply_markup=builders.checklist_items_edit(items, role_slug, shift_type, mode=mode, selected_ids=selected_ids, page=current_page)
        )
    except:
        await callback.answer()

@router.callback_query(F.data.startswith("add_item:"))
async def add_item_start(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    role = parts[1]
    stype = parts[2]
    
    await state.update_data(role=role, shift_type=stype)
    await state.set_state(ChecklistState.waiting_checklist_text)
    
    await callback.message.delete()
    await callback.message.answer(
        f"✍️ <b>Введите текст новой задачи:</b>", 
        reply_markup=reply.cancel()
    )

@router.message(StateFilter(ChecklistState), F.text == "❌ Отмена")
async def cancel_checklist_action(message: Message, state: FSMContext):
    data = await state.get_data()
    role = data.get('role')
    shift_type = data.get('shift_type')
    
    await state.clear()
    
    await message.answer("Действие отменено.", reply_markup=reply.admin_main())

@router.message(ChecklistState.waiting_checklist_text)
async def ask_item_type(message: Message, state: FSMContext):
    await state.update_data(text=message.text.strip())
    await state.set_state(ChecklistState.waiting_checklist_type)
    
    kb = builders.InlineKeyboardBuilder()
    kb.button(text="📝 Обычное", callback_data="type:simple")
    kb.button(text="📸 Фото-отчет", callback_data="type:photo")
    kb.button(text="🎥 Видео-отчет", callback_data="type:video")
    kb.adjust(1)
    
    await message.answer("Какой отчет требуется от сотрудника?", reply_markup=kb.as_markup())

@router.callback_query(ChecklistState.waiting_checklist_type, F.data.startswith("type:"))
async def save_checklist_item(callback: CallbackQuery, state: FSMContext, restaurant_id: int):
    item_type = callback.data.split(":")[1]
    data = await state.get_data()
    
    await check_repo.add_checklist_item(restaurant_id, data['role'], data['shift_type'], data['text'], item_type)
    
    types_map = {"simple": "Обычное", "photo": "Фото", "video": "Видео"}
    
    await callback.message.answer(
        f"✅ Добавлено: <b>{data['text']}</b> ({types_map.get(item_type)})", 
        reply_markup=ReplyKeyboardRemove()
    )
    
    await state.clear()
    await render_checklist_items(callback, restaurant_id, data['role'], data['shift_type'], mode="view")