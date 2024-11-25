import asyncio
import logging
from aiogram import Bot, Dispatcher
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
import handlers
from data.database import DataBase

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Настройки бота
dp = Dispatcher()


async def main():
    try:
        load_dotenv()
        Token = os.getenv('BOT_TOKEN')
        bot = Bot(Token)
        dp = Dispatcher()
        db = DataBase()

        # Добавляем обработчик shutdown для корректного закрытия соединения
        async def shutdown(dispatcher):
            await db.close()
            await bot.session.close()  # Закрываем сессию бота
        
        dp.startup.register(db.create)
        dp.shutdown.register(shutdown)

        # Включаем роутеры
        dp.include_router(handlers.questrionaire.router)
        dp.include_router(handlers.costumes.router)  # Возвращаем роутер костюмов

        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, db=db)
        logger.info("Bot started successfully")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
