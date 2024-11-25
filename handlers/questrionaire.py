from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from data.database import DataBase
from utils.states import Form
from keyboards.reply import rmk, user_menu, admin_menu
from data.models import Role

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: DataBase):
    """
    Начало регистрации пользователя или показ меню
    """
    try:
        # Проверяем, существует ли пользователь
        user = await db.get(message.from_user.id)
        if user:
            # Определяем клавиатуру в зависимости от роли
            keyboard = admin_menu if user.role == Role.Admin else user_menu
            await message.answer(
                "Добро пожаловать в главное меню! ",
                reply_markup=keyboard
            )
            return

        # Начинаем регистрацию
        await state.set_state(Form.full_name)
        await message.answer(
            "Добро пожаловать! Давайте начнем регистрацию.\n\n"
            "Как вас зовут? (Введите ФИО)",
            reply_markup=rmk
        )
    except Exception as e:
        print(f"Error in cmd_start: {e}")

@router.message(Form.full_name)
async def process_name(message: Message, state: FSMContext):
    """
    Обработка ввода ФИО
    """
    try:
        # Проверяем формат ФИО (минимум два слова)
        name_parts = message.text.strip().split()
        if len(name_parts) < 2:
            await message.answer(
                "Пожалуйста, введите полное ФИО (минимум имя и фамилия)"
            )
            return

        await state.update_data(full_name=message.text.strip())
        await state.set_state(Form.phone)
        await message.answer(
            "Введите ваш номер телефона в формате +7XXXXXXXXXX",
            reply_markup=rmk
        )
    except Exception as e:
        print(f"Error in process_name: {e}")

@router.message(Form.phone)
async def process_phone(message: Message, state: FSMContext, db: DataBase):
    """
    Обработка ввода номера телефона и завершение регистрации
    """
    try:
        phone = message.text.strip()
        # Простая валидация номера телефона
        if not (phone.startswith('+7') and len(phone) == 12 and phone[1:].isdigit()):
            await message.answer(
                "Неверный формат номера телефона. Пожалуйста, используйте формат +7XXXXXXXXXX"
            )
            return

        # Сохраняем все данные
        user_data = await state.get_data()
        user_data.update({
            "id": message.from_user.id,
            "phone": phone,
            "role": Role.User
        })

        # Сохраняем в базу данных
        await db.insert(**user_data)
        await state.clear()

        # Отправляем сообщение об успешной регистрации
        await message.answer(
            "Регистрация успешно завершена! \n"
            "Добро пожаловать в нашу систему!",
            reply_markup=user_menu
        )
    except Exception as e:
        print(f"Error in process_phone: {e}")
        await message.answer(
            "Произошла ошибка при регистрации. Пожалуйста, попробуйте позже или обратитесь в поддержку."
        )
