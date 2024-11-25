import asyncio
import sys
import os
from pathlib import Path

# Добавляем родительскую директорию в PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from data.database import DataBase
from data.models import Costumes

# Список костюмов для добавления
COSTUMES = [
    {
        "name": "Костюм Пирата",
        "image_url": "https://s2.radikal.cloud/2024/11/21/photo_2024-09-17_21-51-27.jpeg",
        "size": "M",
        "quantity": 2
    },
    {
        "name": "Костюм Ковбоя",
        "image_url": "https://s2.radikal.cloud/2024/11/21/photo_2024-09-17_21-51-27.jpeg",
        "size": "L",
        "quantity": 1
    },
    {
        "name": "Костюм Супермена",
        "image_url": "https://s2.radikal.cloud/2024/11/21/photo_2024-09-17_21-51-27.jpeg",
        "size": "XL",
        "quantity": 1
    },
    {
        "name": "Костюм Джокера",
        "image_url": "https://s2.radikal.cloud/2024/11/21/photo_2024-09-17_21-51-27.jpeg",
        "size": "M",
        "quantity": 1
    },
    {
        "name": "Костюм Шерлока Холмса",
        "image_url": "https://s2.radikal.cloud/2024/11/21/photo_2024-09-17_21-51-27.jpeg",
        "size": "L",
        "quantity": 1
    },
    {
        "name": "Костюм Зорро",
        "image_url": "https://s2.radikal.cloud/2024/11/21/photo_2024-09-17_21-51-27.jpeg",
        "size": "M",
        "quantity": 1
    },
    {
        "name": "Костюм Гангстера",
        "image_url": "https://s2.radikal.cloud/2024/11/21/photo_2024-09-17_21-51-27.jpeg",
        "size": "XL",
        "quantity": 2
    },
    {
        "name": "Костюм Викинга",
        "image_url": "https://s2.radikal.cloud/2024/11/21/photo_2024-09-17_21-51-27.jpeg",
        "size": "L",
        "quantity": 1
    },
    {
        "name": "Костюм Мушкетера",
        "image_url": "https://s2.radikal.cloud/2024/11/21/photo_2024-09-17_21-51-27.jpeg",
        "size": "M",
        "quantity": 1
    },
    {
        "name": "Костюм Дракулы",
        "image_url": "https://s2.radikal.cloud/2024/11/21/photo_2024-09-17_21-51-27.jpeg",
        "size": "L",
        "quantity": 1
    }
]

async def add_costumes():
    db = DataBase()
    await db.create()  # Убедимся, что база данных создана

    try:
        async with db.async_session() as session:
            for costume_data in COSTUMES:
                # Создаем новый костюм
                new_costume = Costumes(**costume_data)
                session.add(new_costume)
                print(f"Добавлен костюм: {costume_data['name']}")
            
            await session.commit()
            print("\nВсе костюмы успешно добавлены в базу данных!")
    
    except Exception as e:
        print(f"Ошибка при добавлении костюмов: {e}")
    
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(add_costumes())
