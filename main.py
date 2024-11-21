import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
import sys
import os
from dotenv import load_dotenv
from uuid import uuid4


# Загрузка переменных окружения из файла .env
load_dotenv()
# Настройки бота
dp = Dispatcher()

# Список костюмов
costumes = [
    {
        "title": "Казачий костюм",
        "description": "Мужской, полный комплект, 48 размер",
        "size": "48",
        "image_url": "https://s2.radikal.cloud/2024/11/21/photo_2024-10-04_12-22-24.jpeg",
        "code": "COSTUME001",
    },
    {
        "title": "Костюм фаната Нирваны",
        "description": "Мужской, потрёпанный в боях, без сигареты, 48 размер",
        "size": "48",
        "image_url": "https://s2.radikal.cloud/2024/11/21/photo_2024-09-29_19-22-50.jpeg",
        "code": "COSTUME002",
    },
    {
        "title": "Костюм цыгана",
        "description": "Мужской, дорогой, 50 размер",
        "size": "50",
        "image_url": "https://s2.radikal.cloud/2024/11/21/photo_2024-09-17_21-51-27.jpeg",
        "code": "COSTUME003",
    },
]


@dp.inline_query()
async def inline_query_handler(query: InlineQuery):
    query_text = query.query.strip().lower()  # Убираем лишние пробелы и приводим к нижнему регистру
    results = []

    # Фильтрация костюмов
    for costume in costumes:
        if query_text in costume["title"].lower() or query_text in costume["description"].lower():
            # Формируем результат для Inline Mode
            results.append(
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title=f"{costume['title']} ({costume['size']} размер)",
                    description=costume["description"],
                    input_message_content=InputTextMessageContent(
                        message_text=(
                            f"<b>{costume['title']}</b>\n"
                            f"Описание: {costume['description']}\n"
                            f"Размер: {costume['size']}\n"
                            f"Код костюма: {costume['code']}"
                        ),
                        parse_mode="HTML",
                    ),
                    thumb_url=costume["image_url"],  # Миниатюра
                )
            )

    # Если нет совпадений
    if not results:
        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Ничего не найдено",
                description="Попробуй изменить запрос",
                input_message_content=InputTextMessageContent(
                    message_text="К сожалению, ничего не найдено по вашему запросу."
                ),
            )
        )

    # Отправка результатов
    await query.answer(results, cache_time=1, is_personal=True)


async def main():
    TOKEN = os.getenv('BOT_TOKEN')
    
    # Регистрация хэндлеров и запуск бота
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # Запуск диспетчера
    await dp.start_polling(bot)
    print("Бот запущен.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
