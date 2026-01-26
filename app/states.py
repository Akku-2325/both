from aiogram.fsm.state import State, StatesGroup

class LoginState(StatesGroup):
    waiting_pin = State()

class AddStaffState(StatesGroup):
    waiting_for_id = State()
    waiting_for_name = State()
    waiting_for_role = State()
    waiting_for_pin = State()

class TaskState(StatesGroup):
    waiting_text = State()
    waiting_reward = State()
    waiting_hours = State()
    waiting_employee = State()

class ShiftState(StatesGroup):
    waiting_for_shift_type = State()
    waiting_for_photo_start = State() 
    waiting_for_photo_end = State()

class BalanceState(StatesGroup):
    waiting_for_amount = State()

class MoneyState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_reason = State()