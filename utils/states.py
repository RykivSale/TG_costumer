from aiogram.fsm.state import StatesGroup, State


class Form(StatesGroup):
    full_name = State()
    phone = State()

class CostumeRent(StatesGroup):
    selecting = State()
    confirming = State()

class CostumeReturn(StatesGroup):
    select_costume = State()
    confirm_return = State()
    approve_return = State()  # Для админов

class Search(StatesGroup):
    costume_search = State()
    user_search = State()

class Menu(StatesGroup):
    main = State()
    my_costumes = State()
    return_requests = State()  # Для админов