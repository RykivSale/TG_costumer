from aiogram.types import PhotoSize
from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
import os
from uuid import uuid4
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Инициализация ImageKit
imagekit = ImageKit(
    private_key=os.getenv('IMAGEKIT_PRIVATE_KEY'),
    public_key=os.getenv('IMAGEKIT_PUBLIC_KEY'),
    url_endpoint=os.getenv('IMAGEKIT_URL_ENDPOINT')
)

async def process_costume_image(file_path: str) -> str:
    """
    Обработка изображения костюма с загрузкой в ImageKit.
    
    Args:
        file_path (str): Путь к файлу изображения
        
    Returns:
        str: URL загруженного изображения
    """
    try:
        # Генерируем уникальное имя файла
        file_name = f"costume_{str(uuid4())}.jpg"
        
        # Загружаем файл в ImageKit
        with open(file_path, 'rb') as image_file:
            upload = imagekit.upload_file(
                file=image_file,
                file_name=file_name,
                options=UploadFileRequestOptions(
                    response_fields=["is_private_file", "tags"],
                    tags=["costume"]
                )
            )
        
        # Возвращаем URL загруженного изображения
        return upload.url
        
    except Exception as e:
        print(f"Error uploading image: {str(e)}")
        # В случае ошибки возвращаем URL по умолчанию
        return "https://s2.radikal.cloud/2024/11/21/photo_2024-09-17_21-51-27.jpeg"
