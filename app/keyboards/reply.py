from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

def guest():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔐 Войти")]], 
        resize_keyboard=True
    )

def login_cancel():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена ввода")]],
        resize_keyboard=True
    )

def menu_shift_closed():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🟢 Начать смену")],
            [KeyboardButton(text="📜 История смен"), KeyboardButton(text="💰 Мой баланс")],
            [KeyboardButton(text="🚪 Выйти")]
        ],
        resize_keyboard=True
    )

def menu_shift_open(web_app_url: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚡️ Онлайн Чек-лист")], 
            [KeyboardButton(text="🔴 Закончить смену")],
            [KeyboardButton(text="📜 История смен"), KeyboardButton(text="💰 Мой баланс")],
            # [KeyboardButton(text="📋 Открыть WebApp", web_app=WebAppInfo(url=web_app_url))],
        ],
        resize_keyboard=True
    )

def admin_main():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👀 Мониторинг")], 
            [KeyboardButton(text="👥 Список сотрудников")],
            [KeyboardButton(text="📝 Дать задание"), KeyboardButton(text="🗑 Отменить задание")],
            [KeyboardButton(text="📋 История заданий")],
            [KeyboardButton(text="➕ Добавить сотрудника"), KeyboardButton(text="🗑 Удалить сотрудника")],
            [KeyboardButton(text="🚪 Выйти из админки")]
        ],
        resize_keyboard=True
    )

def cancel():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )

def roles():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="barista"), KeyboardButton(text="cashier")],
            [KeyboardButton(text="cook"), KeyboardButton(text="admin")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

# 👇 ДОБАВЛЯЕМ ЭТУ ФУНКЦИЮ
def shift_type_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌅 Утренняя"), KeyboardButton(text="🌇 Вечерняя")],
            [KeyboardButton(text="📅 Полный день")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )