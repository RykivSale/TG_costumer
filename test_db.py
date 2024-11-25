import asyncio
import asyncpg
from dotenv import load_dotenv
import os

async def create_database():
    load_dotenv()
    
    try:
        # Сначала подключаемся к стандартной базе postgres
        conn = await asyncpg.connect(
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            host=os.getenv('POSTGRES_HOST'),
            port=os.getenv('POSTGRES_PORT'),
            database='postgres'  # Подключаемся к стандартной базе
        )
        
        # Проверяем существование базы данных bot
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            os.getenv('POSTGRES_DB')
        )
        
        if not exists:
            # Создаем базу данных bot, если она не существует
            await conn.execute(f"CREATE DATABASE {os.getenv('POSTGRES_DB')}")
            print(f"База данных {os.getenv('POSTGRES_DB')} успешно создана!")
        else:
            print(f"База данных {os.getenv('POSTGRES_DB')} уже существует.")
        
        await conn.close()
        
        # Теперь пробуем подключиться к новой базе данных
        new_conn = await asyncpg.connect(
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            host=os.getenv('POSTGRES_HOST'),
            port=os.getenv('POSTGRES_PORT'),
            database=os.getenv('POSTGRES_DB')
        )
        
        version = await new_conn.fetchval('SELECT version()')
        print("Подключение к новой базе данных успешно!")
        print(f"Версия PostgreSQL: {version}")
        
        await new_conn.close()
        
    except Exception as e:
        print(f"Ошибка: {str(e)}")

if __name__ == "__main__":
    asyncio.run(create_database())
