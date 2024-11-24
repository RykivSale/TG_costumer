from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

main = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Моя анкета"),
            KeyboardButton(text="Статистика")
        ],
        [
            KeyboardButton(text="Начать поиск")
        ]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

rmk = ReplyKeyboardRemove()


reply_logined = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Start connecting",callback_data='View')],
        [KeyboardButton(text="My matches",callback_data='Matches')],
        [KeyboardButton(text="Connection requests",callback_data='WhoLikes')],
        [KeyboardButton(text="Profile settings",callback_data='Options')]
    ],resize_keyboard=True,
        input_field_placeholder="")

reply_search= ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👍",callback_data='like')],
        [KeyboardButton(text="👎",callback_data='dislike')],
        [KeyboardButton(text="🚫",callback_data='stop')]
    ],resize_keyboard=True,
        input_field_placeholder="")

