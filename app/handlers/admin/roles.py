import uuid
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from app.database.repo import users as user_repo, roles as role_repo
from app.keyboards import reply, builders
from app.states.states import RoleState

router = Router()

@router.message(StateFilter("*"), F.text == "🔙 В Главное меню")
async def back_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню", reply_markup=reply.admin_main())

@router.callback_query(StateFilter("*"), F.data == "back_to_admin")
async def back_admin_inline(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Панель управления", reply_markup=reply.admin_main())

@router.message(StateFilter("*"), F.text == "🎭 Роли")
async def roles_menu(message: Message, state: FSMContext, restaurant_id: int):
    await state.clear()
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    await message.answer("🎭 <b>Управление ролями:</b>", reply_markup=reply.admin_roles_menu())

@router.message(StateFilter("*"), F.text == "➕ Добавить роль")
async def add_role_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(RoleState.waiting_role_name)
    await message.answer("✍️ Название роли (на русском):", reply_markup=reply.cancel())

@router.message(RoleState.waiting_role_name)
async def add_role_finish(message: Message, state: FSMContext, restaurant_id: int):
    if message.text == "❌ Отмена": return await back_main(message, state)
    slug = f"role_{uuid.uuid4().hex[:6]}"
    await role_repo.add_role(restaurant_id, slug, message.text.strip())
    await state.clear()
    await message.answer(f"✅ Роль добавлена!", reply_markup=reply.admin_roles_menu())

@router.message(StateFilter("*"), F.text == "📝 Редактировать роль")
async def edit_role_list(message: Message, state: FSMContext, restaurant_id: int):
    await state.clear()
    roles = await role_repo.get_all_roles(restaurant_id)
    await message.answer("Какую переименовать?", reply_markup=builders.dynamic_role_select(roles, "edit_role_name"))

@router.callback_query(F.data.startswith("edit_role_name:"))
async def edit_role_name_start(callback: CallbackQuery, state: FSMContext, restaurant_id: int):
    slug = callback.data.split(":")[1]
    role = await role_repo.get_role(restaurant_id, slug)
    await state.update_data(slug=slug)
    await state.set_state(RoleState.waiting_new_role_name)
    await callback.message.edit_text(f"✍️ Новое имя для <b>{role['name']}</b>:", reply_markup=None)

@router.message(RoleState.waiting_new_role_name)
async def edit_role_name_finish(message: Message, state: FSMContext, restaurant_id: int):
    if message.text == "❌ Отмена": return await back_main(message, state)
    data = await state.get_data()
    await role_repo.update_role_name(restaurant_id, data['slug'], message.text.strip())
    await state.clear()
    await message.answer("✅ Изменено.", reply_markup=reply.admin_roles_menu())

@router.message(StateFilter("*"), F.text == "❌ Удалить роль")
async def del_role_start(message: Message, state: FSMContext, restaurant_id: int):
    await state.clear()
    roles = await role_repo.get_all_roles(restaurant_id)
    await message.answer("Какую роль удалить?", reply_markup=builders.delete_role_select(roles))

@router.callback_query(F.data.startswith("del_role_db:"))
async def ask_delete_role(callback: CallbackQuery, restaurant_id: int):
    slug = callback.data.split(":")[1]
    role = await role_repo.get_role(restaurant_id, slug)
    
    role_name = role['name'] if role else "Неизвестно"
    
    await callback.message.edit_text(
        f"⚠️ <b>ВЫ УВЕРЕНЫ?</b>\n\n"
        f"Вы хотите удалить роль: <b>{role_name}</b>.\n"
        f"Если есть сотрудники с этой ролью, у них могут возникнуть проблемы.",
        reply_markup=builders.confirm_delete_role_menu(slug)
    )

@router.callback_query(F.data == "cancel_del_role")
async def cancel_delete_role(callback: CallbackQuery, restaurant_id: int):
    roles = await role_repo.get_all_roles(restaurant_id)
    await callback.message.edit_text("Какую роль удалить?", reply_markup=builders.delete_role_select(roles))

@router.callback_query(F.data.startswith("confirm_del_role:"))
async def confirm_delete_role(callback: CallbackQuery, restaurant_id: int):
    slug = callback.data.split(":")[1]
    
    await role_repo.delete_role(restaurant_id, slug)
    
    roles = await role_repo.get_all_roles(restaurant_id)
    if not roles:
        await callback.message.edit_text("Список ролей пуст (кроме Админа).")
    else:
        await callback.message.edit_text("✅ Роль удалена.\nКакую роль удалить?", reply_markup=builders.delete_role_select(roles))
    
    await callback.answer("Роль успешно удалена")