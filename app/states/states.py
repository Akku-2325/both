from aiogram.fsm.state import State, StatesGroup

class RootState(StatesGroup):
    active = State()
    waiting_target_id = State()
    waiting_broadcast_text = State()

class OwnerReg(StatesGroup):
    waiting_key = State()
    waiting_title = State()
    waiting_name = State()
    waiting_pin = State()

class LoginState(StatesGroup):
    waiting_pin = State()

class RegState(StatesGroup):
    name = State()
    pin = State()

class TaskState(StatesGroup):
    waiting_text = State()
    waiting_reward = State()
    waiting_hours = State()
    waiting_employee = State()

class ShiftState(StatesGroup):
    waiting_for_shift_type = State()
    waiting_for_photo_start = State() 
    waiting_for_photo_end = State()
    waiting_checklist_comment = State() 
    waiting_end_comment = State()       

class MoneyState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_reason = State()

class RoleState(StatesGroup):
    waiting_role_name = State()
    waiting_role_slug = State()
    waiting_new_role_name = State()

class ChecklistState(StatesGroup):
    waiting_checklist_text = State()

class ReminderState(StatesGroup):
    remind_role = State()
    remind_text = State()
    remind_interval = State()