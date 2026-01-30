from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart, StateFilter, CommandObject
from app.database.repo import saas as saas_repo
from app.database.repo import users as user_repo
from app.keyboards import reply

router = Router()

class OwnerReg(StatesGroup):
    waiting_key = State()
    waiting_title = State()
    waiting_name = State()
    waiting_pin = State()

# ВАЖНО: Этот хендлер сработает ТОЛЬКО если в ссылке есть "LICENSE-"
@router.message(CommandStart(deep_link=True), F.text.contains("LICENSE-"), StateFilter("*"))
async def start_owner_registration(message: Message, state: FSMContext, command: CommandObject):
    args = command.args
    await state.clear() # Сброс любых зависших состояний

    key_data = await saas_repo.get_license_key(args)
    
    if not key_data: 
        return await message.answer("⛔ Ключ лицензии не найден.")
    
    if key_data['is_used']:
        return await message.answer("⚠️ Эта лицензия уже была активирована.")

    # Проверка на персональную привязку (по ID или Username)
    current_username = message.from_user.username
    current_id = message.from_user.id
    
    if key_data['target_tg_id'] and key_data['target_tg_id'] != current_id:
         return await message.answer("⛔ ОШИБКА: Ссылка заблокирована для другого пользователя.")

    if key_data['target_username']:
        clean_target = key_data['target_username'].lstrip('@').lower()
        clean_current = current_username.lower() if current_username else ""
        if clean_target != clean_current:
            return await message.answer(f"⛔ ОШИБКА: Ссылка заблокирована для @{key_data['target_username']}.")

    await state.update_data(key=args)
    await process_key(message, args, state)

@router.message(OwnerReg.waiting_key)
async def key_input(message: Message, state: FSMContext):
    await process_key(message, message.text.strip(), state)

async def process_key(message: Message, key: str, state: FSMContext):
    # Повторная проверка, чтобы не дублировать код
    key_data = await saas_repo.get_license_key(key)
    if not key_data or key_data['is_used']:
        return await message.answer("⛔ Ключ недействителен.")
    
    await state.update_data(key=key)
    await state.set_state(OwnerReg.waiting_title)
    await message.answer("✅ <b>Лицензия подтверждена!</b>\n\n1️⃣ Введите <b>название новой кофейни</b>:")

@router.message(OwnerReg.waiting_title)
async def reg_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(OwnerReg.waiting_name)
    await message.answer("2️⃣ Введите ваше <b>Имя</b> (Владельца):")

@router.message(OwnerReg.waiting_name)
async def reg_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(OwnerReg.waiting_pin)
    await message.answer("3️⃣ Установите <b>PIN-код</b> (4 цифры) для входа:")

@router.message(OwnerReg.waiting_pin)
async def reg_pin(message: Message, state: FSMContext):
    if not message.text.isdigit() or len(message.text) != 4:
        return await message.answer("❌ PIN должен содержать 4 цифры.")
    
    data = await state.get_data()
    pin_hash = user_repo.hash_pin(message.text)
    
    success = await saas_repo.register_new_restaurant(
        data['title'], message.from_user.id, message.from_user.username, 
        data['name'], pin_hash, data['key']
    )
    
    await state.clear()
    
    if success:
        await message.answer(
            f"🎉 <b>Кофейня «{data['title']}» успешно создана!</b>\n\n"
            f"Вход доступен по кнопке ниже.",
            reply_markup=reply.guest() 
        )
    else:
        await message.answer("⛔ Ошибка: Лицензия была использована.", reply_markup=reply.guest())