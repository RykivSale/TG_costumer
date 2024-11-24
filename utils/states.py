from aiogram.fsm.state import StatesGroup, State


class Form(StatesGroup):
    user_type = State()
    bio = State()
    goal = State()
    check = State()
    submit = State()
    
class Menu(StatesGroup):
    view = State()
    options = State()
    
class Edit(StatesGroup):
    user_type = State()
    bio = State()
    goal = State()
  