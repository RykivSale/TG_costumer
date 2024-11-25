from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
import os

imagekit = ImageKit(
    private_key='private_rkOl7FZgsJX8dgEq/aYQAd60qKY=',
    public_key='public_6cvNEFlA7P9+pXI5cJdAlO/vuu4=',
    url_endpoint='https://ik.imagekit.io/digitalcostumer/'
)

# Путь к локальному файлу
FILE_PATH = r"C:\Users\coolm\Pictures\nature-animal-wildlife-mammal-monkey-fauna-primate-face-ape-orangutan-vertebrate-orang-utan-great-ape-929263.jpg"

try:
    # Открываем файл в бинарном режиме
    with open(FILE_PATH, 'rb') as file:
        # Получаем только имя файла без пути
        file_name = os.path.basename(FILE_PATH)
        
        # Загружаем файл
        upload = imagekit.upload_file(
            file=file,
            file_name=file_name,
            options=UploadFileRequestOptions(
                response_fields=["is_private_file", "tags"],
                tags=["tag1", "tag2"]
            )
        )
        
        # Выводим результат
        print("Upload successful!")
        print("URL:", upload.url)
        print("File ID:", upload.file_id)
        
except Exception as e:
    print(f"Error uploading file: {str(e)}")
