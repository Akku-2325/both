from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.config import WEB_APP_URL, ADMIN_PIN  
from app.database.repo import users as user_repo
from app.database.repo import shifts as shift_repo

from app.services import auth as auth_service
from app.keyboards import reply
from app.states import LoginState

router = Router()

@router.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext): 
    await state.clear() 
    
    role = await user_repo.get_session_role(message.from_user.id)
    
    if role == "admin":
        await message.answer("🕴 Вы <b>Администратор</b>.", reply_markup=reply.admin_main())
    elif role:
        # 👇 ИСПРАВЛЕНИЕ: Получаем имя сотрудника, чтобы не писать "Привет, cashier"
        user = await user_repo.get_user(message.from_user.id)
        name = user['full_name'] if user else role
        
        await message.answer(f"👋 Привет, <b>{name}</b>.", reply_markup=reply.menu_shift_closed())
    else:
        await message.answer("👋 Добро пожаловать!", reply_markup=reply.guest())


@router.message(Command("admin_login"))
async def admin_login_cmd(message: Message):
    if not message.text:
        return
        
    parts = message.text.split()
    if len(parts) < 2 or parts[1] != ADMIN_PIN:
        await message.answer("❌ Неверный пароль администратора.")
        return
    
    await user_repo.create_session(message.from_user.id, "admin")
    await message.answer("🕴 <b>Панель управления.</b>", reply_markup=reply.admin_main())

@router.message(F.text == "🔐 Войти")
async def login_start(message: Message, state: FSMContext):
    await state.set_state(LoginState.waiting_pin)
    await message.answer("🔢 Введите PIN-код:", reply_markup=reply.login_cancel())

@router.message(StateFilter("*"), F.text == "❌ Отмена ввода")
async def cancel_login_global(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Вход отменен.", reply_markup=reply.guest())

@router.message(LoginState.waiting_pin)
async def login_process(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Пожалуйста, введите PIN-код цифрами (текстом).")
        return

    result = await auth_service.try_login(message.from_user.id, message.text.strip())

    if result == "disabled":
        await message.answer("⛔ Аккаунт отключен.", reply_markup=reply.guest())
        await state.clear()
    elif result: 
        await state.clear()
        user = result
        if user["role"] == "admin":
            await message.answer(f"😎 Шеф {user['full_name']}, панель открыта.", reply_markup=reply.admin_main())
        else:
            active_shift = await shift_repo.get_active_shift(user['tg_id'])
            if active_shift:
                await message.answer(f"✅ С возвращением, {user['full_name']}! Смена идет.", reply_markup=reply.menu_shift_open(WEB_APP_URL))
            else:
                await message.answer(f"✅ Привет, {user['full_name']}!", reply_markup=reply.menu_shift_closed())
    else:
        await message.answer("❌ Неверный PIN. Попробуйте еще раз.")

@router.message(F.text.in_({"🚪 Выйти", "🚪 Выйти из админки"}))
async def logout_cmd(message: Message, state: FSMContext):
    await state.clear()
    await auth_service.logout(message.from_user.id)
    await message.answer("👋 До свидания.", reply_markup=reply.guest())