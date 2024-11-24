
from aiogram import Router, F
from aiogram.types import Message,KeyboardButton,ReplyKeyboardMarkup
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from keyboards.builders import reply_builder
from keyboards.reply import main, rmk,reply_logined

from data.database import DataBase
from utils.states import Form


router = Router()

@router.message(CommandStart())
async def my_form(message: Message, state: FSMContext, db: DataBase):
    try:
        is_exists = await db.get(message.from_user.id)
        if is_exists is not None:
            usr = await db.get(message.from_user.id)
            await message.answer(
                """
                Welcome back to Web3Connect! 

Are you ready to continue with more connections?🌍🚀
                """,
                reply_markup=reply_logined
            )
        else:
            await state.set_state(Form.user_type)
            await message.answer(
                """
                Hey there! Welcome to Web3Connect! 🌍🚀

You’ve just found the coolest spot to meet and team up with folks in the Web3 world. Let’s quickly set up your profile so you can start making those key connections!
                """,
                reply_markup=rmk
            )
            await message.answer(
                """
                Step 1: What’s Your Scene?
                
First up, what do you do? <b>Pick one</b>:""",
                reply_markup=reply_builder(["Startup", "Investor", "Web3 expert", "Service provider"]),
                parse_mode=ParseMode.HTML,
                input_field_placeholder="First up, what do you do?"
            )
    except Exception as e:
        # Вывести ошибку в консоль
        print(f"An error occurred: {e}")



@router.message(Form.user_type, F.text.in_(["Startup", "Investor","Web3 expert","Service provider"]))
async def form_bio(message: Message, state: FSMContext):
    try:
        await state.update_data(user_type=message.text)
        user_data = await state.get_data()

        await state.set_state(Form.bio)
        await message.answer("""
<b>Bio Time</b>
Step 2: Share Your Story

Who are you? Where are you from? Got any cool Web3 stories or skills? This is your spot to shine and tell your future connections what you’re all about.

Example:

Yo! I’m Jordan, hanging in Berlin. Been coding up smart contracts for 3 years and now I’m building a cool dApp for creators. Big on green tech and open-source vibes.
                             """, reply_markup=rmk, parse_mode=ParseMode.HTML)
    except Exception as e:
        # Вывести ошибку в консоль
        print(f"An error occurred: {e}")

@router.message(Form.user_type)
async def incorrect_form_user_type(message: Message, state: FSMContext):
    try:
        await message.answer(f"Выбери один вариант!")
    except Exception as e:
        # Вывести ошибку в консоль
        print(f"An error occurred: {e}")



@router.message(Form.bio)
async def form_goal(message: Message, state: FSMContext):
    try:
        await state.update_data(bio=message.text)
        await state.set_state(Form.goal)
        await message.answer("""
<b>Networking Goals</b>
Step 3: What’s Your Quest?

Why are you here? Looking for partners, funding, wisdom, or something else? Let the crowd know what you’re hunting for to link up with the right tribe.

Example:

On the lookout for believers in my latest venture and keen to swap tips on scaling up in the Web3 space. Also, if you’re into creating more secure digital worlds, let’s chat.

                             """, reply_markup=rmk, parse_mode=ParseMode.HTML)
    except Exception as e:
        # Вывести ошибку в консоль
        print(f"An error occurred: {e}")


@router.message(Form.goal)
async def form_check(message: Message, state: FSMContext):
    try:
        await state.update_data(goal=message.text)
        await state.set_state(Form.check)
        user_data = await state.get_data()

        await message.answer(f"""
Just Checking!

You’ve chosen {str(user_data['user_type'])} as your flag. Here’s your story:


{user_data['bio']}

And here’s your quest:

{user_data['goal']}

Need to tweak anything? Hit Edit. All good? Press Submit to jump into the Web3Connect world and start networking!
""",
                             reply_markup=reply_builder(["Edit", "Submit"]),
                             parse_mode=ParseMode.HTML,
                             input_field_placeholder="Press Submit to jump into the Web3Connect world and start networking!")
    except Exception as e:
        # Вывести ошибку в консоль
        print(f"An error occurred: {e}")

@router.message(Form.check, F.text.in_(["Submit"]))
async def form_submit(message: Message, state: FSMContext, db: DataBase):
    try:
        data = await state.get_data()
        data["id"] = message.from_user.id
        data["contact_info"] = message.from_user.username
        data["role"] = 'User'
        data['rating'] = 1
        data['user_type'] = data['user_type'].replace(" ", "_")
        data['status_for_search'] = True
        await db.insert(**data)
        await state.clear()
        await message.answer("""
<b>Welcome to the Family</b>
You’re In! 🎉

Your profile’s all set. Dive into discovering connections or hit up your Dashboard anytime to refresh your profile or find something new.

Let’s Make Some Waves! Remember, the best journeys start with connecting dots.
                             """, reply_markup=reply_logined, parse_mode=ParseMode.HTML)
    except Exception as e:
        # Вывести ошибку в консоль
        print(f"An error occurred: {e}")


@router.message(Form.check, F.text.in_(["Edit"]))
async def form_cancel(message: Message, state: FSMContext):
    try:
        await message.answer("""
                             Let`s try again!
                             """, reply_markup=rmk, parse_mode=ParseMode.HTML)
        await state.clear()
        await state.set_state(Form.user_type)
        await message.answer(
            """
            Step 1: What’s Your Scene?
            
First up, what do you do? <b>Pick one</b>:""",
            reply_markup=reply_builder(["Startup", "Investor", "Web3 expert", "Service provider"]),
            parse_mode=ParseMode.HTML,
            input_field_placeholder="First up, what do you do?"
        )
    except Exception as e:
        # Вывести ошибку в консоль
        print(f"An error occurred: {e}")
