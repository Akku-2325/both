from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from app.core.config import SUPER_ADMIN_PASSWORD
from app.database.repo import saas as saas_repo
from app.keyboards import reply
from app.states.states import RootState

router = Router()

async def get_dashboard_data():
    stats = await saas_repo.get_platform_stats()
    text = (
        f"🌌 <b>SaaS MASTER PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>Кофейни:</b> {stats['cafes']}\n"
        f"👥 <b>Пользователи:</b> {stats['users']}\n"
        f"🟢 <b>Активные смены:</b> {stats['shifts']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>Выберите системное действие:</i>"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="✨ Создать Magic Link", callback_data="root_pre_gen")
    builder.button(text="📋 Список Кофеен", callback_data="root_list_cafes")
    builder.button(text="📢 Рассылка владельцам", callback_data="root_broadcast")
    builder.button(text="🔄 Обновить", callback_data="root_refresh")
    builder.adjust(1)
    return text, builder.as_markup()


@router.message(Command("root_login"))
async def root_login_cmd(message: Message):
    parts = message.text.split()
    if len(parts) < 2 or parts[1] != SUPER_ADMIN_PASSWORD: return
    try: await message.delete()
    except: pass
    
    await message.answer("🔑 <b>Master-доступ активирован.</b>", reply_markup=reply.super_admin_panel())
    
    text, kb = await get_dashboard_data()
    await message.answer(text, reply_markup=kb)

@router.message(F.text == "👑 Панель Владельца")
async def root_panel_btn(message: Message):
    text, kb = await get_dashboard_data()
    await message.answer(text, reply_markup=kb)

@router.callback_query(F.data == "root_refresh")
async def root_refresh_handler(callback: CallbackQuery):
    text, kb = await get_dashboard_data()
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass 
    await callback.answer()

@router.callback_query(F.data == "root_pre_gen")
async def root_gen_ask_tag(callback: CallbackQuery, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏩ Пропустить (Для любого)")],
            [KeyboardButton(text="❌ Отмена")]
        ], 
        resize_keyboard=True
    )
    await state.set_state(RootState.waiting_target_id)
    try: await callback.message.delete()
    except: pass
    await callback.message.answer("🎯 <b>Для кого лицензия?</b>\nВведите @username или нажмите пропустить:", reply_markup=kb)
    await callback.answer()

@router.message(RootState.waiting_target_id)
async def root_gen_finish(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание лицензии отменено.", reply_markup=reply.super_admin_panel())
        dash_text, dash_kb = await get_dashboard_data()
        return await message.answer(dash_text, reply_markup=dash_kb)

    tag = None if message.text == "⏩ Пропустить (Для любого)" else message.text.lstrip("@").strip()
    key = await saas_repo.create_license_key(message.from_user.id, tag)
    info = await bot.get_me()
    await state.clear()
    
    text = f"✨ <b>Magic Link готова!</b>\n\n🔗 <code>https://t.me/{info.username}?start={key}</code>\n\n"
    if tag: text += f"🔒 <b>Для:</b> @{tag}"
    else: text += "🔓 <b>Для всех.</b>"
    
    await message.answer(text, reply_markup=reply.super_admin_panel())
    dash_text, dash_kb = await get_dashboard_data()
    await message.answer(dash_text, reply_markup=dash_kb)

@router.callback_query(F.data == "root_broadcast")
async def root_broadcast_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RootState.waiting_broadcast_text)
    try: await callback.message.delete()
    except: pass
    await callback.message.answer("✍️ <b>Введите текст рассылки:</b>", reply_markup=reply.cancel())
    await callback.answer()

@router.message(RootState.waiting_broadcast_text)
async def root_broadcast_finish(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отмена.", reply_markup=reply.super_admin_panel())
        dash_text, dash_kb = await get_dashboard_data()
        return await message.answer(dash_text, reply_markup=dash_kb)

    owners = await saas_repo.get_all_owners_ids()
    count = 0
    for o_id in owners:
        try:
            await bot.send_message(o_id, f"📢 <b>УВЕДОМЛЕНИЕ:</b>\n\n{message.text}")
            count += 1
        except: pass
        
    await state.clear()
    await message.answer(f"✅ Рассылка завершена. Доставлено: {count}", reply_markup=reply.super_admin_panel())
    dash_text, dash_kb = await get_dashboard_data()
    await message.answer(dash_text, reply_markup=dash_kb)

@router.callback_query(F.data == "root_list_cafes")
async def list_cafes_handler(callback: CallbackQuery):
    cafes = await saas_repo.get_all_restaurants()
    if not cafes: 
        return await callback.answer("Кофеен пока нет.", show_alert=True)
    
    builder = InlineKeyboardBuilder()
    for c in cafes:
        icon = "🟢" if c['is_active'] else "❄️"
        builder.button(text=f"{icon} {c['title']}", callback_data=f"root_manage:{c['id']}")
    builder.button(text="🔙 Назад", callback_data="root_refresh")
    builder.adjust(1)
    
    await callback.message.edit_text("📋 <b>Кофейни в системе:</b>", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("root_manage:"))
async def manage_cafe_view(callback: CallbackQuery):
    r_id = int(callback.data.split(":")[1])
    active = await saas_repo.is_restaurant_active(r_id)
    
    status_text = "АКТИВНА 🟢" if active else "ЗАМОРОЖЕНА ❄️"
    btn_text = "❄️ Заморозить" if active else "🟢 Разморозить"
    
    builder = InlineKeyboardBuilder()
    builder.button(text=btn_text, callback_data=f"root_toggle:{r_id}")
    builder.button(text="🗑 Удалить навсегда", callback_data=f"root_del_ask:{r_id}")
    builder.button(text="🔙 Назад", callback_data="root_list_cafes")
    builder.adjust(1)
    
    await callback.message.edit_text(f"🔧 <b>Управление кофейней #{r_id}</b>\nСтатус: {status_text}", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("root_toggle:"))
async def toggle_cafe_status(callback: CallbackQuery, bot: Bot):
    r_id = int(callback.data.split(":")[1])
    info = await saas_repo.get_restaurant_info(r_id)
    new_status = await saas_repo.toggle_restaurant_status(r_id)
    
    msg = "❄️ Доступ к вашей кофейне заморожен." if new_status == 0 else "🟢 Ваша кофейня разморожена. Можно входить."
    try: await bot.send_message(info['owner_tg_id'], f"⚠️ <b>Оповещение платформы:</b>\n\nКофейня: {info['title']}\n{msg}")
    except: pass
    
    await callback.answer("Статус обновлен")
    await manage_cafe_view(callback)

@router.callback_query(F.data.startswith("root_del_ask:"))
async def delete_cafe_ask(callback: CallbackQuery):
    r_id = int(callback.data.split(":")[1])
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ ПОДТВЕРДИТЬ УДАЛЕНИЕ", callback_data=f"root_del_conf:{r_id}")
    builder.button(text="🔙 Отмена", callback_data=f"root_manage:{r_id}")
    builder.adjust(1)
    await callback.message.edit_text(f"⚠️ <b>Вы уверены?</b>\n\nУдаление кофейни #{r_id} уничтожит все данные (сотрудников, смены, отчеты).", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("root_del_conf:"))
async def delete_cafe_confirm(callback: CallbackQuery, bot: Bot):
    r_id = int(callback.data.split(":")[1])
    info = await saas_repo.get_restaurant_info(r_id)
    users = await saas_repo.get_restaurant_users(r_id)
    
    for u_id in users:
        try: await bot.send_message(u_id, f"🚫 <b>Кофейня '{info['title']}' была удалена из системы.</b>\nВсе сессии завершены.")
        except: pass
        
    await saas_repo.delete_restaurant(r_id)
    await callback.answer("Кофейня успешно удалена", show_alert=True)
    await list_cafes_handler(callback)

@router.message(F.text == "🚪 Выйти из системы")
async def root_logout(message: Message):
    await message.answer("🔒 Мастер-сессия закрыта.", reply_markup=reply.guest())