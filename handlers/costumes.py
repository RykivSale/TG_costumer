from aiogram import Router, F
from aiogram.types import Message, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from aiogram.fsm.context import FSMContext
from data.database import DataBase
from utils.states import CostumeRent
from keyboards.reply import user_menu, admin_menu, confirm_rent_kb
from uuid import uuid4
from sqlalchemy import select, or_, update
from data.models import Costumes, UserCostumes
from datetime import datetime

router = Router()

# Обработчик кнопки "Получить костюм"
@router.message(F.text == "📥 Получить костюм")
async def get_costume_start(message: Message, state: FSMContext):
    await state.set_state(CostumeRent.selecting)
    await message.answer(
        "Начните вводить название костюма или размер.\n"
        "Вы можете искать по:\n"
        "- Названию костюма\n"
        "- Размеру (M, L, XL)\n"
        "Для отмены нажмите любую кнопку в меню.",
        reply_markup=user_menu,
        switch_inline_query_current_chat=""  # Это активирует inline режим в текущем чате
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
            await message.answer(
                f"Вы хотите взять костюм:\n"
                f"🎭 <b>{costume.name}</b>\n"
                f"📏 Размер: {costume.size}\n"
                f"Подтверждаете?",
                reply_markup=confirm_rent_kb,
                parse_mode="HTML"
            )
        else:
            await message.answer("Костюм не найден. Попробуйте выбрать другой.", reply_markup=user_menu)
            await state.set_state(CostumeRent.selecting)

# Обработчик подтверждения аренды
@router.message(CostumeRent.confirming, F.text.in_(["✅ Да", "❌ Нет"]))
async def process_rent_confirmation(message: Message, state: FSMContext, db: DataBase):
    if message.text == "❌ Нет":
        await message.answer("Окей. Продолжай выбор!", reply_markup=user_menu)
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
                await message.answer("Извините, этот костюм уже недоступен.", reply_markup=user_menu)
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

            # Создаем запись об аренде
            new_rent = UserCostumes(
                user_id=message.from_user.id,
                costume_id=costume.id,
                rent_date=datetime.now(),
                returned=False
            )
            session.add(new_rent)
            await session.commit()

            await message.answer(
                f"✅ Отлично! Костюм {costume.name} теперь ваш!\n"
                f"Не забудьте вернуть его в хорошем состоянии.",
                reply_markup=user_menu
            )

        except Exception as e:
            print(f"Error in rent confirmation: {e}")
            await session.rollback()
            await message.answer(
                "Произошла ошибка при оформлении аренды. Попробуйте позже.",
                reply_markup=user_menu
            )

    await state.clear()
