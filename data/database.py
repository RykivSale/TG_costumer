from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from sqlalchemy.exc import NoResultFound, OperationalError
from .models import Base, Users, Costumes, Cart, Role
from dotenv import load_dotenv
import os
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message
import asyncio
import logging
import asyncpg

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataBase:
    def __init__(self):
        try:
            load_dotenv()

            self.POSTGRES_USER = os.getenv('POSTGRES_USER')
            self.POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
            self.POSTGRES_DB = os.getenv('POSTGRES_DB')
            self.POSTGRES_HOST = os.getenv('POSTGRES_HOST')
            self.POSTGRES_PORT = os.getenv('POSTGRES_PORT')

            if not all([self.POSTGRES_USER, self.POSTGRES_PASSWORD, self.POSTGRES_DB, self.POSTGRES_HOST, self.POSTGRES_PORT]):
                raise ValueError("Missing required database configuration in .env file")

            logger.info(f"Connecting to database at {self.POSTGRES_HOST}:{self.POSTGRES_PORT}")
            
            self.DATABASE_URL = f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

        except Exception as e:
            logger.error(f"Error during database initialization: {e}")
            raise

    async def ensure_database_exists(self):
        try:
            # Сначала подключаемся к стандартной базе postgres
            conn = await asyncpg.connect(
                user=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                database='postgres'
            )
            
            # Проверяем существование базы данных
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1",
                self.POSTGRES_DB
            )
            
            if not exists:
                # Создаем базу данных, если она не существует
                await conn.execute(f"CREATE DATABASE {self.POSTGRES_DB}")
                logger.info(f"Database {self.POSTGRES_DB} created successfully!")
            else:
                logger.info(f"Database {self.POSTGRES_DB} already exists.")
            
            await conn.close()
            
            # Создаем engine только после того, как убедились, что база существует
            self.engine = create_async_engine(
                self.DATABASE_URL,
                echo=True,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                connect_args={
                    "command_timeout": 60,
                    "server_settings": {"application_name": "TG_costumer"}
                }
            )
            
            self.async_session = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False
            )
            
            # Проверяем подключение к новой базе
            new_conn = await asyncpg.connect(
                user=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                database=self.POSTGRES_DB
            )
            
            version = await new_conn.fetchval('SELECT version()')
            logger.info(f"Successfully connected to database. PostgreSQL version: {version}")
            
            await new_conn.close()
            
        except Exception as e:
            logger.error(f"Error ensuring database exists: {e}")
            raise

    async def create(self):
        try:
            # Сначала убеждаемся, что база данных существует
            await self.ensure_database_exists()
            
            # Создаем таблицы
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully!")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    async def get(self, user_id: int) -> Users | None:
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(Users).where(Users.id == user_id)
                )
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    async def insert(self, **kwargs):
        try:
            async with self.async_session() as session:
                async with session.begin():
                    new_user = Users(**kwargs)
                    session.add(new_user)
                    await session.commit()
                    logger.info(f"User {kwargs.get('full_name')} successfully inserted!")
        except Exception as e:
            logger.error(f"Error inserting user: {e}")
            raise

    async def get_session(self) -> AsyncSession:
        return self.async_session()

    async def close(self):
        try:
            logger.info("Closing database connection...")
            await self.engine.dispose()
            logger.info("Database connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
            raise

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        data["db"] = self
        return await handler(event, data)


class UserCRUD:

    @staticmethod
    async def create_user(session: AsyncSession, full_name: str, phone: str) -> Users:
        new_user = Users(full_name=full_name, phone=phone, role=Role.User)
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
