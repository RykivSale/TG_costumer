from aiogram.filters.callback_data import CallbackData


class UserAnswerData(CallbackData, prefix="answer"):
    answer: str
    user_id: int | None = None
    username: str | None = None
    
class UserMatchData(CallbackData, prefix="match"):
    answer: str
    user_id: int | None = None
    username: str | None = None