from aiogram import Router, F
from aiogram.filters import Command, StateFilter, CommandStart, CommandObject
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.config import WEB_APP_URL, ADMIN_PIN  
from app.database.repo import users as user_repo
from app.database.repo import shifts as shift_repo
from app.database.repo import checklists as check_repo

from app.services import auth as auth_service
from app.keyboards import reply

class RegState(StatesGroup):
    name = State()
    pin = State()

router = Router()

@router.message(CommandStart(deep_link=True))
async def start_invite(message: Message, command: CommandObject, state: FSMContext):
    invite_code = command.args
    invite_data = await check_repo.check_invite(invite_code)
    
    if not invite_data:
        return await message.answer("⛔ Ссылка недействительна или устарела.")
    
    existing = await user_repo.get_user(message.from_user.id)
    if existing and existing['is_active']:
         return await message.answer("Вы уже зарегистрированы!")

    await state.update_data(role=invite_data['role'], code=invite_code)
    await state.set_state(RegState.name)
    await message.answer(
        f"👋 Добро пожаловать!\nВы регистрируетесь как: <b>{invite_data['role']}</b>\n\n"
        f"1️⃣ Введите ваше <b>Имя и Фамилию</b>:"
    )

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
    await user_repo.add_user(message.from_user.id, data['name'], data['role'], message.text)
    await check_repo.mark_invite_used(data['code'])
    
    await state.clear()
    await message.answer(
        f"✅ Регистрация завершена, {data['name']}!\nТеперь нажмите <b>🔐 Войти</b>.", 
        reply_markup=reply.guest()
    )

@router.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext): 
    await state.clear() 
    role = await user_repo.get_session_role(message.from_user.id)
    
    if role == "admin":
        await message.answer("🕴 Вы <b>Администратор</b>.", reply_markup=reply.admin_main())
    elif role:
        user = await user_repo.get_user(message.from_user.id)
        name = user['full_name'] if user else role
        await message.answer(f"👋 Привет, <b>{name}</b>.", reply_markup=reply.menu_shift_closed())
    else:
        await message.answer("👋 Добро пожаловать! Если у вас есть ссылка-приглашение, перейдите по ней.", reply_markup=reply.guest())

@router.message(Command("admin_login"))
async def admin_login_cmd(message: Message):
    if not message.text: return
    parts = message.text.split()
    if len(parts) < 2 or parts[1] != ADMIN_PIN:
        return await message.answer("❌ Неверный пароль.")
    
    await user_repo.create_session(message.from_user.id, "admin")
    await user_repo.add_user(message.from_user.id, "Главный Админ", "admin", "0000")
    
    await message.answer("🕴 <b>Панель управления.</b>", reply_markup=reply.admin_main())

@router.message(F.text == "🔐 Войти")
async def login_start(message: Message, state: FSMContext):
    await state.set_state("login_pin")
    await message.answer("🔢 Введите PIN-код:", reply_markup=reply.login_cancel())

@router.message(StateFilter("*"), F.text == "❌ Отмена ввода")
async def cancel_login_global(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Вход отменен.", reply_markup=reply.guest())

@router.message(StateFilter("login_pin"))
async def login_process(message: Message, state: FSMContext):
    result = await auth_service.try_login(message.from_user.id, message.text.strip())
    if result == "disabled":
        await message.answer("⛔ Аккаунт отключен.", reply_markup=reply.guest())
        await state.clear()
    elif result: 
        await state.clear()
        if result["role"] == "admin":
            await message.answer("Панель открыта.", reply_markup=reply.admin_main())
        else:
            active_shift = await shift_repo.get_active_shift(result['tg_id'])
            if active_shift:
                await message.answer(f"✅ С возвращением, {result['full_name']}! Смена идет.", reply_markup=reply.menu_shift_open(WEB_APP_URL))
            else:
                await message.answer(f"✅ Привет, {result['full_name']}!", reply_markup=reply.menu_shift_closed())
    else:
        await message.answer("❌ Неверный PIN. Попробуйте еще раз.")

@router.message(F.text.in_({"🚪 Выйти", "🚪 Выйти из админки"}))
async def logout_cmd(message: Message, state: FSMContext):
    await state.clear()
    await auth_service.logout(message.from_user.id)
    await message.answer("👋 До свидания.", reply_markup=reply.guest())