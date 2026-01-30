from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.database.repo import users as user_repo, roles as role_repo, checklists as check_repo
from app.keyboards import builders

router = Router()

@router.message(F.text.in_({"🔗 Приглашения", "🔗 Создать приглашение"}))
async def invite_start(message: Message, restaurant_id: int):
    if await user_repo.get_session_role(message.from_user.id) != "admin": return
    roles = await role_repo.get_all_roles(restaurant_id)
    await message.answer(
        "📝 <b>Для какой роли создать ссылку?</b>", 
        reply_markup=builders.dynamic_role_select(roles, "create_invite", show_admin=True)
    )

@router.callback_query(F.data.startswith("create_invite:"))
async def create_invite_link(callback: CallbackQuery, bot: Bot, restaurant_id: int):
    role_slug = callback.data.split(":")[1]
    role_info = await role_repo.get_role(restaurant_id, role_slug)
    role_name = role_info['name'] if role_info else ("Администратор" if role_slug == "admin" else role_slug)
    
    code = await check_repo.create_invite(restaurant_id, role_slug)
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={code}"
    
    text = (
        f"✅ <b>Ссылка создана!</b>\n\n"
        f"Роль: <b>{role_name}</b>\n"
        f"Ссылка: <code>{link}</code>\n\n"
        f"<i>Отправьте её сотруднику. Она одноразовая.</i>"
    )
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Назад", callback_data="back_to_admin")
    await callback.message.edit_text(text, reply_markup=kb.as_markup())