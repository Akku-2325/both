from aiogram import Router, F
from aiogram.filters import StateFilter, CommandStart, CommandObject, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.core.config import WEB_APP_URL
from app.database.repo import users as user_repo
from app.database.repo import checklists as check_repo
from app.database.repo import roles as role_repo
from app.database.repo import shifts as shift_repo 
from app.services import auth as auth_service
from app.keyboards import reply
from app.states.states import RegState, LoginState

router = Router()

@router.message(CommandStart(deep_link=True), StateFilter("*"))
async def start_employee_invite(message: Message, command: CommandObject, state: FSMContext):
    invite_code = command.args
    await state.clear() 

    invite_data = await check_repo.check_invite(invite_code)
    if not invite_data:
        return await message.answer("⛔ Ссылка приглашения недействительна или устарела.")
    
    target_r_id = invite_data['restaurant_id']
    existing = await user_repo.get_user(message.from_user.id, target_r_id)
    if existing and existing['is_active']:
         return await message.answer("Вы уже зарегистрированы в этом заведении! Нажмите 'Войти'.", reply_markup=reply.guest())

    role_info = await role_repo.get_role(target_r_id, invite_data['role'])
    role_name = role_info['name'] if role_info else invite_data['role']

    await state.update_data(role=invite_data['role'], code=invite_code, target_restaurant_id=target_r_id)
    await state.set_state(RegState.name)
    await message.answer(f"👋 Вас пригласили в команду!\nДолжность: <b>{role_name}</b>\n\n1️⃣ Введите ваше <b>Имя и Фамилию</b>:")

@router.message(Command("start"), StateFilter("*"))
async def start_default(message: Message, state: FSMContext):
    await state.clear()
    
    shops = await user_repo.get_user_restaurants(message.from_user.id)
    
    if not shops:
        await message.answer(
            "👋 Добро пожаловать!\n\n"
            "• Если вы владелец: используйте <b>Magic Link</b> для создания кофейни.\n"
            "• Если вы сотрудник: попросите <b>ссылку-приглашение</b> у менеджера.", 
            reply_markup=reply.guest()
        )
    else:
        await message.answer("👋 С возвращением! Выберите действие:", reply_markup=reply.guest())


@router.message(RegState.name)
async def reg_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(RegState.pin)
    await message.answer("2️⃣ Придумайте <b>PIN-код</b> (4 цифры) для входа:")

@router.message(RegState.pin)
async def reg_pin(message: Message, state: FSMContext):
    if not message.text.isdigit() or len(message.text) != 4:
        return await message.answer("❌ PIN должен состоять из 4 цифр.")
    data = await state.get_data()
    await user_repo.add_user(message.from_user.id, data['target_restaurant_id'], data['name'], data['role'], message.text)
    await check_repo.mark_invite_used(data['code'])
    await state.clear()
    await message.answer(f"✅ Регистрация завершена! Нажмите <b>🔐 Войти</b>.", reply_markup=reply.guest())


@router.message(F.text == "🔐 Войти")
async def login_start(message: Message, state: FSMContext):
    shops = await user_repo.get_user_restaurants(message.from_user.id)
    if not shops: return await message.answer("⚠️ Вы не зарегистрированы нигде.")
    
    if len(shops) == 1:
        shop = shops[0]
        await state.update_data(target_restaurant_id=shop['id'])
        await state.set_state(LoginState.waiting_pin)
        return await message.answer(f"🏢 <b>{shop['title']}</b>\n🔢 Введите PIN-код:", reply_markup=reply.login_cancel())

    builder = InlineKeyboardBuilder()
    for s in shops: builder.button(text=f"🏢 {s['title']}", callback_data=f"login_select:{s['id']}")
    builder.adjust(1)
    await message.answer("<b>Выберите заведение для входа:</b>", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("login_select:"))
async def login_select_shop(callback: CallbackQuery, state: FSMContext):
    r_id = int(callback.data.split(":")[1])
    shops = await user_repo.get_user_restaurants(callback.from_user.id)
    shop = next((s for s in shops if s['id'] == r_id), None)
    
    if not shop: return await callback.answer("Ошибка доступа.")

    await state.update_data(target_restaurant_id=r_id)
    await state.set_state(LoginState.waiting_pin)
    await callback.message.edit_text(f"🏢 <b>{shop['title']}</b>\n🔢 Введите PIN-код:", reply_markup=None)
    await callback.message.answer("Введите ПИН или нажмите отмену:", reply_markup=reply.login_cancel())
    await callback.answer()

@router.message(LoginState.waiting_pin, F.text == "❌ Отмена ввода")
async def login_cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Вход отменен.", reply_markup=reply.guest())

@router.message(LoginState.waiting_pin)
async def login_process(message: Message, state: FSMContext):
    data = await state.get_data()
    r_id = data.get('target_restaurant_id')
    
    if not r_id:
        await state.clear()
        return await message.answer("Ошибка сессии.", reply_markup=reply.guest())

    result = await auth_service.try_login(message.from_user.id, r_id, message.text.strip())
    
    if result == "disabled":
        await message.answer("⛔ Доступ заблокирован администратором.", reply_markup=reply.guest())
        await state.clear()
    elif result: 
        await state.clear()
        if result["role"] == "admin": 
            await message.answer("🕴 Панель управления открыта.", reply_markup=reply.admin_main())
        else:
            active_shift = await shift_repo.get_active_shift(message.from_user.id, r_id)
            if active_shift:
                await message.answer(f"✅ С возвращением, {result['full_name']}!", reply_markup=reply.menu_shift_open(WEB_APP_URL))
            else:
                await message.answer(f"✅ Привет, {result['full_name']}!", reply_markup=reply.menu_shift_closed())
    else:
        await message.answer("❌ Неверный PIN-код.")

@router.message(F.text.in_({"🚪 Выйти", "🚪 Выйти из админки"}))
async def logout_cmd(message: Message, state: FSMContext):
    await state.clear()
    await auth_service.logout(message.from_user.id)
    await message.answer("👋 До свидания.", reply_markup=reply.guest())