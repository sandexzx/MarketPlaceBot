from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_photos = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_manager = State()
    confirm_creation = State()
    
class EditStates(StatesGroup):
    select_ad = State()
    edit_photos = State()
    edit_description = State()
    edit_price = State()
    edit_manager = State()
    confirm_edit = State()