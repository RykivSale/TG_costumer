from aiogram import Router, F, Bot
from aiogram.types import Message, InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, PhotoSize
from aiogram.fsm.context import FSMContext
from data.database import DataBase
from utils.states import CostumeRent, CostumeReturn, ReturnRequestAdmin, AddCostume
from keyboards.reply import user_menu, admin_menu, confirm_rent_kb
from utils.image_handler import process_costume_image
from uuid import uuid4
from sqlalchemy import select, or_, update, delete, join
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from data.models import Costumes, Cart, Users, ReturnRequest, Role
from datetime import datetime, timedelta
import os

router = Router()

# Функция для получения правильного меню на основе роли
async def get_role_menu(user_id: int, db: DataBase):
    user = await db.get(user_id)
    return admin_menu if user and user.role == Role.Admin else user_menu

# Обработчик кнопки "Получить костюм"
@router.message(F.text == "📥 Получить костюм")
async def get_costume_start(message: Message, state: FSMContext, db: DataBase):
    await state.set_state(CostumeRent.selecting)
    
    # Создаем инлайн кнопку, которая активирует режим поиска
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🔍 Искать костюм",
                switch_inline_query_current_chat=""
            )]
        ]
    )
    
    menu = await get_role_menu(message.from_user.id, db)
    
    await message.answer(
        "Нажмите кнопку ниже, чтобы начать поиск костюма.\n"
        "Вы можете искать по:\n"
        "- Названию костюма\n"
        "- Размеру (M, L, XL)\n"
        "Для отмены нажмите любую кнопку в меню.",
        reply_markup=keyboard
    )

# Обработчик inline режима
@router.inline_query()
async def inline_search(query: InlineQuery, db: DataBase):
    search_text = query.query.lower().strip()
    results = []

    try:
        async with db.async_session() as session:
            # Получаем все костюмы из базы
            stmt = select(Costumes).where(
                Costumes.quantity > 0,
                or_(
                    Costumes.name.ilike(f"%{search_text}%"),
                    Costumes.size.ilike(f"%{search_text}%")
                )
            )
            result = await session.execute(stmt)
            costumes = result.scalars().all()

            # Формируем результаты для inline режима
            for costume in costumes:
                results.append(
                    InlineQueryResultArticle(
                        id=str(costume.costume_uuid),
                        title=f"{costume.name} (Размер: {costume.size})",
                        description=f"В наличии: {costume.quantity} шт.",
                        thumb_url=costume.image_url,
                        input_message_content=InputTextMessageContent(
                            message_text=f"COSTUME_UUID:{costume.costume_uuid}"
                        )
                    )
                )

    except Exception as e:
        print(f"Error in inline search: {e}")
        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Произошла ошибка при поиске",
                description="Пожалуйста, попробуйте позже",
                input_message_content=InputTextMessageContent(
                    message_text="К сожалению, произошла ошибка при поиске костюмов. Попробуйте позже."
                )
            )
        ]

    if not results:
        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Ничего не найдено",
                description="Попробуйте изменить поисковый запрос",
                input_message_content=InputTextMessageContent(
                    message_text="По вашему запросу ничего не найдено. Попробуйте другие параметры поиска."
                )
            )
        ]

    await query.answer(
        results=results,
        cache_time=5,
        is_personal=True
    )

# Обработчик выбора костюма
@router.message(CostumeRent.selecting, F.text.startswith("COSTUME_UUID:"))
async def process_costume_selection(message: Message, state: FSMContext, db: DataBase):
    costume_uuid = message.text.split(":")[1]
    
    # Сохраняем UUID костюма в состоянии
    await state.update_data(costume_uuid=costume_uuid)
    await state.set_state(CostumeRent.confirming)
    
    # Получаем информацию о костюме
    async with db.async_session() as session:
        stmt = select(Costumes).where(Costumes.costume_uuid == costume_uuid)
        result = await session.execute(stmt)
        costume = result.scalar_one_or_none()
        
        if costume:
            # Удаляем сообщение с UUID
            await message.delete()
            
            # Отправляем сообщение с подтверждением
            menu = await get_role_menu(message.from_user.id, db)
            await message.answer(
                f"Вы хотите взять костюм:\n"
                f"🎭 <b>{costume.name}</b>\n"
                f"📏 Размер: {costume.size}\n"
                f"Подтверждаете?",
                reply_markup=confirm_rent_kb,
                parse_mode="HTML"
            )
        else:
            menu = await get_role_menu(message.from_user.id, db)
            await message.answer("Костюм не найден. Попробуйте выбрать другой.", reply_markup=menu)
            await state.set_state(CostumeRent.selecting)

# Обработчик подтверждения аренды
@router.message(CostumeRent.confirming, F.text.in_(["✅ Да", "❌ Нет"]))
async def process_rent_confirmation(message: Message, state: FSMContext, db: DataBase):
    if message.text == "❌ Нет":
        menu = await get_role_menu(message.from_user.id, db)
        await message.answer("Окей. Продолжай выбор!", reply_markup=menu)
        await state.set_state(CostumeRent.selecting)
        return

    # Получаем UUID костюма из состояния
    data = await state.get_data()
    costume_uuid = data.get("costume_uuid")

    async with db.async_session() as session:
        try:
            # Получаем костюм и проверяем количество
            stmt = select(Costumes).where(Costumes.costume_uuid == costume_uuid)
            result = await session.execute(stmt)
            costume = result.scalar_one_or_none()

            if not costume or costume.quantity <= 0:
                menu = await get_role_menu(message.from_user.id, db)
                await message.answer("Извините, этот костюм уже недоступен.", reply_markup=menu)
                await state.clear()
                return

            # Уменьшаем количество костюмов
            stmt = update(Costumes).where(
                Costumes.costume_uuid == costume_uuid,
                Costumes.quantity > 0
            ).values(
                quantity=Costumes.quantity - 1
            )
            await session.execute(stmt)

            # Создаем запись в корзине
            new_cart_item = Cart(
                user_id=message.from_user.id,
                costume_id=costume.id
            )
            session.add(new_cart_item)

            await session.commit()

            menu = await get_role_menu(message.from_user.id, db)
            await message.answer(
                f"✅ Отлично! Костюм {costume.name} теперь ваш!\n"
                f"Не забудьте вернуть его в хорошем состоянии.",
                reply_markup=menu
            )

        except Exception as e:
            print(f"Error in rent confirmation: {e}")
            await session.rollback()
            menu = await get_role_menu(message.from_user.id, db)
            await message.answer(
                "Произошла ошибка при оформлении аренды. Попробуйте позже.",
                reply_markup=menu
            )

    await state.clear()

# Обработчик кнопки "Мои костюмы"
@router.message(F.text == "👔 Мои костюмы")
async def my_costumes(message: Message, db: DataBase):
    async with db.async_session() as session:
        try:
            # Получаем все костюмы пользователя через Cart
            stmt = select(Costumes).join(Cart).where(
                Cart.user_id == message.from_user.id
            )
            result = await session.execute(stmt)
            costumes = result.scalars().all()

            menu = await get_role_menu(message.from_user.id, db)

            if not costumes:
                await message.answer(
                    "У вас пока нет арендованных костюмов. 📦\n"
                    "Чтобы арендовать костюм, нажмите '📥 Получить костюм'.",
                    reply_markup=menu
                )
                return

            # Формируем сообщение со списком костюмов
            response = "👔 Ваши арендованные костюмы:\n\n"
            for costume in costumes:
                response += (
                    f"🎭 <b>{costume.name}</b>\n"
                    f"📏 Размер: {costume.size}\n"
                    f"🖼️ Фото: {costume.image_url}\n\n"
                )

            await message.answer(
                response,
                parse_mode="HTML",
                reply_markup=menu
            )

        except Exception as e:
            print(f"Error in my_costumes: {e}")
            menu = await get_role_menu(message.from_user.id, db)
            await message.answer(
                "Произошла ошибка при получении списка костюмов. Попробуйте позже.",
                reply_markup=menu
            )

# Обработчик кнопки "Сдать костюм"
@router.message(F.text == "📤 Сдать костюм")
async def return_costume_start(message: Message, state: FSMContext, db: DataBase):
    await state.set_state(CostumeReturn.select_costume)
    
    async with db.async_session() as session:
        # Получаем костюмы пользователя в корзине
        stmt = select(Costumes).join(Cart).where(
            Cart.user_id == message.from_user.id
        )
        result = await session.execute(stmt)
        costumes = result.scalars().all()

        menu = await get_role_menu(message.from_user.id, db)

        if not costumes:
            await message.answer(
                "У вас нет костюмов для сдачи. 🤷‍♀️\n"
                "Сначала арендуйте костюм в разделе '📥 Получить костюм'.",
                reply_markup=menu
            )
            await state.clear()
            return

        # Создаем inline клавиатуру с костюмами
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{costume.name} (Размер: {costume.size})", 
                callback_data=f"return_costume:{costume.id}"
            )] for costume in costumes
        ])

        await message.answer(
            "Выберите костюм, который хотите сдать:",
            reply_markup=keyboard
        )

# Обработчик выбора костюма для возврата
@router.callback_query(CostumeReturn.select_costume, F.data.startswith("return_costume:"))
async def process_costume_return_selection(callback: CallbackQuery, state: FSMContext, db: DataBase):
    costume_id = int(callback.data.split(":")[1])
    
    # Сохраняем ID костюма в состоянии
    await state.update_data(costume_id=costume_id)
    await state.set_state(CostumeReturn.confirm_return)

    # Получаем информацию о костюме
    async with db.async_session() as session:
        try:
            # Используем joinedload для загрузки связанных данных
            stmt = select(Costumes).where(Costumes.id == costume_id)
            result = await session.execute(stmt)
            costume = result.scalar_one_or_none()

            if costume:
                # Создаем inline-клавиатуру для подтверждения
                confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Да", callback_data="confirm_return:yes"),
                        InlineKeyboardButton(text="❌ Нет", callback_data="confirm_return:no")
                    ]
                ])

                await callback.message.edit_text(
                    f"Вы хотите сдать костюм:\n"
                    f"🎭 <b>{costume.name}</b>\n"
                    f"📏 Размер: {costume.size}\n"
                    "Подтверждаете возврат?",
                    reply_markup=confirm_keyboard,
                    parse_mode="HTML"
                )
            else:
                menu = await get_role_menu(callback.from_user.id, db)
                await callback.message.answer(
                    "Костюм не найден.", 
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="В меню", callback_data="to_menu")]
                    ])
                )
                await state.clear()
        except Exception as e:
            print(f"Error in process_costume_return_selection: {e}")
            menu = await get_role_menu(callback.from_user.id, db)
            await callback.message.answer(
                "Произошла ошибка при обработке заявки.",
                reply_markup=menu
            )
            await state.clear()

# Обработчик подтверждения возврата
@router.callback_query(CostumeReturn.confirm_return, F.data.startswith("confirm_return:"))
async def process_return_confirmation(callback: CallbackQuery, state: FSMContext, db: DataBase):
    confirmation = callback.data.split(":")[1]
    
    # Получаем ID костюма из состояния
    data = await state.get_data()
    costume_id = data.get("costume_id")

    async with db.async_session() as session:
        try:
            # Создаем заявку на возврат
            new_return_request = ReturnRequest(
                user_id=callback.from_user.id,
                costume_id=costume_id,
                status='pending'
            )
            session.add(new_return_request)

            # Удаляем запись из корзины
            stmt = delete(Cart).where(
                Cart.user_id == callback.from_user.id,
                Cart.costume_id == costume_id
            )
            await session.execute(stmt)

            await session.commit()

            # Создаем inline-клавиатуру для возврата в меню
            menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="В меню", callback_data="to_menu")]
            ])

            await callback.message.edit_text(
                "✅ Заявка на возврат костюма создана!\n"
                "Администратор рассмотрит вашу заявку в ближайшее время.",
                reply_markup=menu_keyboard
            )

        except Exception as e:
            print(f"Error in return confirmation: {e}")
            await session.rollback()
            
            # Создаем inline-клавиатуру для возврата в меню
            menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="В меню", callback_data="to_menu")]
            ])

            await callback.message.edit_text(
                "Произошла ошибка при создании заявки на возврат. Попробуйте позже.",
                reply_markup=menu_keyboard
            )

    await state.clear()

# Обработчик возврата в меню
@router.callback_query(F.data == "to_menu")
async def return_to_menu(callback: CallbackQuery, db: DataBase):
    # Удаляем текущее сообщение с inline клавиатурой
    await callback.message.delete()
    
    # Отправляем новое сообщение с reply клавиатурой
    menu = await get_role_menu(callback.from_user.id, db)
    await callback.message.answer(
        "Выберите действие:", 
        reply_markup=menu
    )

# Обработчик возврата в меню администратора
@router.callback_query(F.data == "to_admin_menu")
async def return_to_admin_menu(callback: CallbackQuery, db: DataBase):
    # Удаляем текущее сообщение с inline клавиатурой
    await callback.message.delete()
    
    user = await db.get(callback.from_user.id)
    if user and user.role == Role.Admin:
        await callback.message.answer(
            "Выберите действие:", 
            reply_markup=admin_menu
        )
    else:
        menu = await get_role_menu(callback.from_user.id, db)
        await callback.message.answer(
            "У вас нет прав администратора.", 
            reply_markup=menu
        )

# Обработчик кнопки "Заявки на сдачу" для администратора
@router.message(F.text == "📋 Заявки на сдачу")
async def list_return_requests(message: Message, state: FSMContext, db: DataBase):
    # Проверяем роль пользователя
    user = await db.get(message.from_user.id)
    if not user or user.role != Role.Admin:
        menu = await get_role_menu(message.from_user.id, db)
        await message.answer(
            "У вас нет прав для просмотра заявок на возврат.",
            reply_markup=menu
        )
        return

    async with db.async_session() as session:
        try:
            # Получаем все pending заявки на возврат с жадной загрузкой связанных данных
            stmt = select(ReturnRequest).where(ReturnRequest.status == 'pending').options(
                joinedload(ReturnRequest.costume),
                joinedload(ReturnRequest.user)
            )
            result = await session.execute(stmt)
            return_requests = result.scalars().all()

            if not return_requests:
                await message.answer(
                    "📭 На данный момент нет активных заявок на возврат костюмов.",
                    reply_markup=admin_menu
                )
                await state.clear()
                return

            # Создаем inline клавиатуру с заявками
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"Костюм: {request.costume.name} (Размер: {request.costume.size}) | От: {request.user.full_name}", 
                    callback_data=f"return_request:{request.id}"
                )] for request in return_requests
            ] + [[InlineKeyboardButton(text="↩️ Назад", callback_data="to_admin_menu")]])

            await message.answer(
                "📋 Список активных заявок на возврат:\n"
                "Выберите заявку для обработки:",
                reply_markup=keyboard
            )
            await state.set_state(ReturnRequestAdmin.list_requests)

        except Exception as e:
            print(f"Error in list_return_requests: {e}")
            await message.answer(
                "Произошла ошибка при получении заявок на возврат.",
                reply_markup=admin_menu
            )
            await state.clear()

# Обработчик выбора заявки на возврат
@router.callback_query(ReturnRequestAdmin.list_requests, F.data.startswith("return_request:"))
async def process_return_request_selection(callback: CallbackQuery, state: FSMContext, db: DataBase):
    request_id = int(callback.data.split(":")[1])
    
    # Сохраняем ID заявки в состоянии
    await state.update_data(request_id=request_id)
    await state.set_state(ReturnRequestAdmin.confirm_request)

    # Получаем информацию о заявке
    async with db.async_session() as session:
        try:
            # Используем joinedload для загрузки связанных данных
            stmt = select(ReturnRequest).where(ReturnRequest.id == request_id).options(
                joinedload(ReturnRequest.costume),
                joinedload(ReturnRequest.user)
            )
            result = await session.execute(stmt)
            return_request = result.scalar_one_or_none()

            if return_request:
                # Создаем inline-клавиатуру для подтверждения
                confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_return_request:yes"),
                        InlineKeyboardButton(text="❌ Отклонить", callback_data="confirm_return_request:no")
                    ]
                ])

                await callback.message.edit_text(
                    f"Заявка на возврат:\n"
                    f"🎭 Костюм: <b>{return_request.costume.name}</b>\n"
                    f"📏 Размер: {return_request.costume.size}\n"
                    f"👤 От: {return_request.user.full_name}\n"
                    "Подтверждаете возврат?",
                    reply_markup=confirm_keyboard,
                    parse_mode="HTML"
                )
            else:
                menu = await get_role_menu(callback.from_user.id, db)
                await callback.message.answer(
                    "Заявка не найдена.", 
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="В меню", callback_data="to_admin_menu")]
                    ])
                )
                await state.clear()
        except Exception as e:
            print(f"Error in process_return_request_selection: {e}")
            menu = await get_role_menu(callback.from_user.id, db)
            await callback.message.answer(
                "Произошла ошибка при обработке заявки.",
                reply_markup=menu
            )
            await state.clear()

# Обработчик подтверждения возврата заявки
@router.callback_query(ReturnRequestAdmin.confirm_request, F.data.startswith("confirm_return_request:"))
async def process_return_request_confirmation(callback: CallbackQuery, state: FSMContext, db: DataBase):
    confirmation = callback.data.split(":")[1]
    
    # Получаем ID заявки из состояния
    data = await state.get_data()
    request_id = data.get("request_id")

    async with db.async_session() as session:
        try:
            # Получаем заявку с жадной загрузкой
            stmt = select(ReturnRequest).where(ReturnRequest.id == request_id).options(
                joinedload(ReturnRequest.costume),
                joinedload(ReturnRequest.user)
            )
            result = await session.execute(stmt)
            return_request = result.scalar_one_or_none()

            if not return_request:
                raise ValueError("Заявка не найдена")

            if confirmation == "yes":
                # Увеличиваем количество костюма
                costume_stmt = update(Costumes).where(
                    Costumes.id == return_request.costume_id
                ).values(quantity=Costumes.quantity + 1)
                await session.execute(costume_stmt)

                # Обновляем статус заявки
                return_request.status = 'approved'
            else:
                # Обновляем статус заявки
                return_request.status = 'rejected'

            await session.commit()

            # Создаем inline-клавиатуру для возврата в меню
            menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="В меню", callback_data="to_admin_menu")]
            ])

            await callback.message.edit_text(
                f"Заявка {'подтверждена' if confirmation == 'yes' else 'отклонена'}.\n"
                f"Костюм: {return_request.costume.name}",
                reply_markup=menu_keyboard
            )

        except Exception as e:
            print(f"Error in return request confirmation: {e}")
            await session.rollback()
            
            # Создаем inline-клавиатуру для возврата в меню
            menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="В меню", callback_data="to_admin_menu")]
            ])

            await callback.message.edit_text(
                "Произошла ошибка при обработке заявки на возврат. Попробуйте позже.",
                reply_markup=menu_keyboard
            )

    await state.clear()

# Обработчик кнопки "Поиск костюма" (только для админов)
@router.message(F.text == "🔍 Поиск костюма")
async def search_costumes(message: Message, db: DataBase):
    # Проверяем, является ли пользователь администратором
    user = await db.get(message.from_user.id)
    if not user or user.role != Role.Admin:
        await message.answer("У вас нет доступа к этой функции.")
        return

    # Получаем все активные записи в корзине
    async with db.async_session() as session:
        query = select(Cart, Users, Costumes).join(Users, Cart.user_id == Users.id).join(
            Costumes, Cart.costume_id == Costumes.id
        )
        result = await session.execute(query)
        cart_items = result.all()

        if not cart_items:
            await message.answer("🎉 Отличные новости! Все костюмы свободны и доступны для аренды!")
            return

        # Формируем красивый текст со списком занятых костюмов
        response_text = "📋 Список занятых костюмов:\n\n"
        
        for cart, user, costume in cart_items:
            # Рассчитываем количество дней владения
            days_owned = (datetime.now() - cart.created_at).days + 1
            
            response_text += (
                f"👔 *{costume.name}*\n"
                f"👤 Арендатор: {user.full_name}\n"
                f"📱 Телефон: {user.phone}\n"
                f"⏳ Дней в аренде: {days_owned}\n"
                f"📅 Дата получения: {cart.created_at.strftime('%d.%m.%Y')}\n"
                "➖➖➖➖➖➖➖➖➖➖\n"
            )

        await message.answer(response_text, parse_mode="Markdown")

# Обработчик кнопки "Арендованные костюмы" (только для админов)
@router.message(F.text == "👗 Арендованные костюмы")
async def rented_costumes(message: Message, db: DataBase):
    # Проверяем, является ли пользователь администратором
    user = await db.get(message.from_user.id)
    if not user or user.role != Role.Admin:
        await message.answer("У вас нет доступа к этой функции.")
        return

    # Получаем все активные записи в корзине и заявки на возврат
    async with db.async_session() as session:
        # Получаем активные аренды
        cart_query = select(Cart, Users, Costumes).join(Users, Cart.user_id == Users.id).join(
            Costumes, Cart.costume_id == Costumes.id
        )
        cart_result = await session.execute(cart_query)
        cart_items = cart_result.all()

        # Получаем заявки на возврат
        return_query = select(ReturnRequest, Users, Costumes).join(
            Users, ReturnRequest.user_id == Users.id
        ).join(
            Costumes, ReturnRequest.costume_id == Costumes.id
        ).where(
            ReturnRequest.status == 'pending'
        )
        return_result = await session.execute(return_query)
        return_requests = return_result.all()

        if not cart_items and not return_requests:
            await message.answer("🎉 Отличные новости! Все костюмы свободны и доступны для аренды!")
            return

        # Формируем текст со списком арендованных костюмов
        response_text = "👗 Арендованные костюмы:\n\n"
        
        # Добавляем активные аренды
        if cart_items:
            response_text += "📦 АКТИВНЫЕ АРЕНДЫ:\n"
            for cart, user, costume in cart_items:
                # Рассчитываем количество дней владения
                days_owned = (datetime.now() - cart.created_at).days + 1
                
                response_text += (
                    f"👔 *{costume.name}*\n"
                    f"👤 Арендатор: {user.full_name}\n"
                    f"📱 Телефон: {user.phone}\n"
                    f"⏳ Дней в аренде: {days_owned}\n"
                    f"📅 Дата получения: {cart.created_at.strftime('%d.%m.%Y')}\n"
                    "➖➖➖➖➖➖➖➖➖➖\n"
                )

        # Добавляем заявки на возврат
        if return_requests:
            response_text += "\n📤 ЗАЯВКИ НА ВОЗВРАТ:\n"
            for return_request, user, costume in return_requests:
                response_text += (
                    f"👔 *{costume.name}*\n"
                    f"👤 От: {user.full_name}\n"
                    f"📱 Телефон: {user.phone}\n"
                    f"📝 Статус: Ожидает подтверждения\n"
                    "➖➖➖➖➖➖➖➖➖➖\n"
                )

        # Отправляем сообщение частями, если оно слишком длинное
        if len(response_text) > 4096:
            for x in range(0, len(response_text), 4096):
                await message.answer(response_text[x:x+4096], parse_mode="Markdown")
        else:
            await message.answer(response_text, parse_mode="Markdown")

# Обработчик кнопки "Должники" (только для админов)
@router.message(F.text == "💰 Должники")
async def debtors_list(message: Message, db: DataBase):
    # Проверяем, является ли пользователь администратором
    user = await db.get(message.from_user.id)
    if not user or user.role != Role.Admin:
        await message.answer("У вас нет доступа к этой функции.")
        return

    # Получаем все активные аренды костюмов и заявки на возврат
    async with db.async_session() as session:
        # Получаем активные аренды
        cart_query = (
            select(Users, Costumes, Cart)
            .join(Cart, Users.id == Cart.user_id)
            .join(Costumes, Cart.costume_id == Costumes.id)
        )
        cart_result = await session.execute(cart_query)
        rentals = cart_result.all()

        # Получаем заявки на возврат
        return_query = (
            select(Users, Costumes, ReturnRequest)
            .join(ReturnRequest, Users.id == ReturnRequest.user_id)
            .join(Costumes, ReturnRequest.costume_id == Costumes.id)
            .where(ReturnRequest.status == 'pending')
        )
        return_result = await session.execute(return_query)
        return_requests = return_result.all()

        if not rentals and not return_requests:
            await message.answer("🎉 Отлично! На данный момент нет арендованных костюмов!")
            return

        # Группируем костюмы по пользователям
        user_rentals = {}
        user_returns = {}

        # Группируем активные аренды
        for user, costume, cart in rentals:
            if user.id not in user_rentals:
                user_rentals[user.id] = {
                    'user': user,
                    'costumes': []
                }
            days_owned = (datetime.now() - cart.created_at).days + 1
            user_rentals[user.id]['costumes'].append({
                'name': costume.name,
                'days': days_owned,
                'date': cart.created_at
            })

        # Группируем заявки на возврат
        for user, costume, return_request in return_requests:
            if user.id not in user_returns:
                user_returns[user.id] = {
                    'user': user,
                    'costumes': []
                }
            user_returns[user.id]['costumes'].append({
                'name': costume.name,
                'status': 'pending'
            })

        # Формируем текст ответа
        response_text = "👥 Список должников:\n\n"

        # Добавляем активные аренды
        if user_rentals:
            response_text += "📦 АКТИВНЫЕ АРЕНДЫ:\n"
            for user_data in user_rentals.values():
                user = user_data['user']
                response_text += f"👤 *{user.full_name}*\n📱 Телефон: {user.phone}\n📋 Костюмы:\n"
                
                for costume in user_data['costumes']:
                    response_text += (
                        f"  • {costume['name']}\n"
                        f"    ⏳ Дней в аренде: {costume['days']}\n"
                        f"    📅 Получен: {costume['date'].strftime('%d.%m.%Y')}\n"
                    )
                response_text += "➖➖➖➖➖➖➖➖➖➖\n"

        # Добавляем заявки на возврат
        if user_returns:
            response_text += "\n📤 ЗАЯВКИ НА ВОЗВРАТ:\n"
            for user_data in user_returns.values():
                user = user_data['user']
                response_text += f"👤 *{user.full_name}*\n📱 Телефон: {user.phone}\n📋 Костюмы на возврат:\n"
                
                for costume in user_data['costumes']:
                    response_text += (
                        f"  • {costume['name']}\n"
                        f"    📝 Статус: Ожидает подтверждения\n"
                    )
                response_text += "➖➖➖➖➖➖➖➖➖➖\n"
        
        # Отправляем сообщение частями, если оно слишком длинное
        if len(response_text) > 4096:
            for x in range(0, len(response_text), 4096):
                await message.answer(response_text[x:x+4096], parse_mode="Markdown")
        else:
            await message.answer(response_text, parse_mode="Markdown")

# Обработчик кнопки "➕ Добавить костюм"
@router.message(F.text == "➕ Добавить костюм")
async def add_costume_start(message: Message, state: FSMContext, db: DataBase):
    # Проверяем, является ли пользователь админом
    async with db.async_session() as session:
        user = await session.execute(select(Users).where(Users.id == message.from_user.id))
        user = user.scalar()
        if not user or user.role != Role.Admin:
            await message.answer("У вас нет прав для выполнения этой команды.")
            return

    await message.answer("Введите название костюма:")
    await state.set_state(AddCostume.input_name)

# Обработчик ввода названия костюма
@router.message(AddCostume.input_name)
async def process_costume_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите размер костюма:")
    await state.set_state(AddCostume.input_size)

# Обработчик ввода размера костюма
@router.message(AddCostume.input_size)
async def process_costume_size(message: Message, state: FSMContext):
    await state.update_data(size=message.text)
    await message.answer("Введите количество (будет создана одна запись):")
    await state.set_state(AddCostume.input_quantity)

# Обработчик ввода количества костюма
@router.message(AddCostume.input_quantity)
async def process_costume_quantity(message: Message, state: FSMContext):
    try:
        quantity = int(message.text)
        if quantity <= 0:
            await message.answer("Количество должно быть положительным числом. Попробуйте снова:")
            return
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число. Попробуйте снова:")
        return

    await state.update_data(quantity=quantity)
    await message.answer("Пожалуйста, отправьте фотографию костюма:")
    await state.set_state(AddCostume.input_image)

# Обработчик отправки фотографии костюма
@router.message(AddCostume.input_image, F.photo)
async def process_costume_image_handler(message: Message, state: FSMContext, bot: Bot):
    # Получаем последнюю (самую большую) версию фото
    photo = message.photo[-1]
    
    # Скачиваем файл
    file_info = await bot.get_file(photo.file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    
    # Сохраняем во временный файл
    temp_path = f"temp_costume_{uuid4()}.jpg"
    with open(temp_path, 'wb') as new_file:
        new_file.write(downloaded_file.read())
    
    # Обрабатываем изображение через нашу функцию
    image_url = await process_costume_image(temp_path)
    
    # Удаляем временный файл
    os.remove(temp_path)
    
    data = await state.get_data()
    data['image_url'] = image_url
    await state.update_data(data)

    # Формируем сообщение для подтверждения
    confirm_message = (
        f"Пожалуйста, проверьте данные:\n\n"
        f"Название: {data['name']}\n"
        f"Размер: {data['size']}\n"
        f"Количество: {data['quantity']}\n\n"
        f"Всё верно?"
    )
    
    await message.answer(confirm_message, reply_markup=confirm_rent_kb)
    await state.set_state(AddCostume.confirm)

# Обработчик ошибки отправки фотографии костюма
@router.message(AddCostume.input_image)
async def process_costume_image_error(message: Message):
    await message.answer("Пожалуйста, отправьте фотографию костюма (не файл и не текст):")

# Обработчик подтверждения добавления костюма
@router.message(AddCostume.confirm)
async def process_costume_confirmation(message: Message, state: FSMContext, db: DataBase):
    if message.text == "✅ Да":
        data = await state.get_data()
        
        async with db.async_session() as session:
            new_costume = Costumes(
                name=data['name'],
                size=data['size'],
                quantity=data['quantity'],
                image_url=data['image_url'],
                costume_uuid=str(uuid4())
            )
            session.add(new_costume)
            await session.commit()

        await message.answer("✅ Костюм успешно добавлен!", reply_markup=admin_menu)
    elif message.text == "❌ Нет":
        await message.answer("🚫 Добавление костюма отменено. Спасибо!", reply_markup=admin_menu)
    else:
        await message.answer("Пожалуйста, используйте кнопки для ответа.", reply_markup=confirm_rent_kb)
        return
    
    await state.clear()
