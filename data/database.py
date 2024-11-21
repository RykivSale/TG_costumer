from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from sqlalchemy.exc import NoResultFound
from .models import Base, Users, Costumes, Cart
from dotenv import load_dotenv
import os

class DataBase:

    def __init__(self):
        try:
            load_dotenv()

            POSTGRES_USER = os.getenv('POSTGRES_USER')
            POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
            POSTGRES_DB = os.getenv('POSTGRES_DB')
            POSTGRES_HOST = os.getenv('POSTGRES_HOST')
            POSTGRES_PORT = os.getenv('POSTGRES_PORT')

            # Пример использования подключения к базе данных
            DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}/bot"
            
            # Создание ас

            # Создание асинхронного движка для работы с базой данных Postgres
            self.engine: AsyncEngine = create_async_engine(DATABASE_URL)
            
            # Создание асинхронной сессии для выполнения запросов к базе данных
            self.async_session: AsyncSession = async_sessionmaker(
                self.engine,
                expire_on_commit=False,
                class_=AsyncSession
            )
        except Exception as e:
            # Вывести ошибку в консоль, если что-то пошло не так при инициализации соединения
            print(f"An error occurred during database connection initialization: {e}")

    async def get_session(self):
        """ Получение сессии для выполнения запросов """
        async with self.async_session() as session:
            yield session

    async def init_db(self):
        """ Инициализация базы данных (создание таблиц) """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

class UserCRUD:

    @staticmethod
    async def create_user(session: AsyncSession, full_name: str, phone: str, role: str) -> Users:
        new_user = Users(full_name=full_name, phone=phone, role=role)
        session.add(new_user)
        await session.commit()
        return new_user

    @staticmethod
    async def get_user_by_phone(session: AsyncSession, phone: str) -> Users:
        stmt = select(Users).filter(Users.phone == phone)
        result = await session.execute(stmt)
        user = result.scalars().first()
        if not user:
            raise NoResultFound(f"User with phone {phone} not found.")
        return user

    @staticmethod
    async def update_user_role(session: AsyncSession, user_id: int, new_role: str) -> Users:
        stmt = select(Users).filter(Users.id == user_id)
        result = await session.execute(stmt)
        user = result.scalars().first()
        if user:
            user.role = new_role
            await session.commit()
            return user
        else:
            raise NoResultFound(f"User with id {user_id} not found.")

    @staticmethod
    async def delete_user(session: AsyncSession, user_id: int) -> bool:
        stmt = select(Users).filter(Users.id == user_id)
        result = await session.execute(stmt)
        user = result.scalars().first()
        if user:
            await session.delete(user)
            await session.commit()
            return True
        return False


class CostumeCRUD:

    @staticmethod
    async def create_costume(session: AsyncSession, name: str, image_url: str, size: str = None, quantity: int = 1) -> Costumes:
        new_costume = Costumes(name=name, image_url=image_url, size=size, quantity=quantity)
        session.add(new_costume)
        await session.commit()
        return new_costume

    @staticmethod
    async def get_costume_by_id(session: AsyncSession, costume_id: int) -> Costumes:
        stmt = select(Costumes).filter(Costumes.id == costume_id)
        result = await session.execute(stmt)
        costume = result.scalars().first()
        if not costume:
            raise NoResultFound(f"Costume with id {costume_id} not found.")
        return costume

    @staticmethod
    async def update_costume_quantity(session: AsyncSession, costume_id: int, new_quantity: int) -> Costumes:
        stmt = select(Costumes).filter(Costumes.id == costume_id)
        result = await session.execute(stmt)
        costume = result.scalars().first()
        if costume:
            costume.quantity = new_quantity
            await session.commit()
            return costume
        else:
            raise NoResultFound(f"Costume with id {costume_id} not found.")

    @staticmethod
    async def delete_costume(session: AsyncSession, costume_id: int) -> bool:
        stmt = select(Costumes).filter(Costumes.id == costume_id)
        result = await session.execute(stmt)
        costume = result.scalars().first()
        if costume:
            await session.delete(costume)
            await session.commit()
            return True
        return False

class CartCRUD:

    @staticmethod
    async def add_to_cart(session: AsyncSession, user_id: int, costume_id: int) -> Cart:
        new_cart_item = Cart(user_id=user_id, costume_id=costume_id)
        session.add(new_cart_item)
        await session.commit()
        return new_cart_item

    @staticmethod
    async def get_cart_by_user(session: AsyncSession, user_id: int) -> list:
        stmt = select(Cart).filter(Cart.user_id == user_id)
        result = await session.execute(stmt)
        cart_items = result.scalars().all()
        return cart_items

    @staticmethod
    async def remove_from_cart(session: AsyncSession, cart_item_id: int) -> bool:
        stmt = select(Cart).filter(Cart.id == cart_item_id)
        result = await session.execute(stmt)
        cart_item = result.scalars().first()
        if cart_item:
            await session.delete(cart_item)
            await session.commit()
            return True
        return False

    @staticmethod
    async def clear_cart(session: AsyncSession, user_id: int) -> bool:
        stmt = select(Cart).filter(Cart.user_id == user_id)
        result = await session.execute(stmt)
        cart_items = result.scalars().all()
        if cart_items:
            for item in cart_items:
                await session.delete(item)
            await session.commit()
            return True
        return False
