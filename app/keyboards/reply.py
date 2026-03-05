from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def admin_main():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👀 Мониторинг"), KeyboardButton(text="📜 Журнал смен")], 
            [KeyboardButton(text="👥 Сотрудники"), KeyboardButton(text="🔗 Приглашения")],
            [KeyboardButton(text="📝 Задания")],
            [KeyboardButton(text="⚙️ Чек-листы"), KeyboardButton(text="🎭 Роли")],
            [KeyboardButton(text="🔔 Напоминания"), KeyboardButton(text="🚪 Выйти из админки")]
        ],
        resize_keyboard=True
    )

def admin_roles_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить роль"), KeyboardButton(text="📝 Редактировать роль")],
            [KeyboardButton(text="❌ Удалить роль"), KeyboardButton(text="🔙 В Главное меню")]
        ],
        resize_keyboard=True
    )

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
        ],
        resize_keyboard=True
    )

def cancel():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )

def comment_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➡️ Пропустить")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

def shift_type_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌅 Утренняя"), KeyboardButton(text="🌇 Вечерняя")],
            [KeyboardButton(text="📅 Полный день")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

def super_admin_panel():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👑 Панель Владельца")],
            [KeyboardButton(text="🚪 Выйти из системы")]
        ],
        resize_keyboard=True
    )