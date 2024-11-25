from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Клавиатура для обычных пользователей
user_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📥 Получить костюм"),
            KeyboardButton(text="📤 Сдать костюм")
        ],
        [
            KeyboardButton(text="👔 Мои костюмы")
        ]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие"
)

# Клавиатура для администраторов
admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📥 Получить костюм"),
            KeyboardButton(text="📤 Сдать костюм")
        ],
        [
            KeyboardButton(text="👔 Мои костюмы"),
            KeyboardButton(text="➕ Добавить костюм")
        ],
        [
            KeyboardButton(text="📋 Заявки на сдачу")
        ],
        [
            KeyboardButton(text="👗 Арендованные костюмы"),
            KeyboardButton(text="💰 Должники")
        ]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие"
)

# Клавиатура подтверждения аренды
confirm_rent_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="✅ Да"),
            KeyboardButton(text="❌ Нет")
        ]
    ],
    resize_keyboard=True
)

rmk = ReplyKeyboardRemove()
