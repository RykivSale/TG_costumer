from sqlalchemy import Column, BigInteger, Text, String, Integer, Boolean, ForeignKey, Enum, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql.schema import UniqueConstraint
from enum import Enum as PythonEnum
import uuid
from datetime import datetime

Base = declarative_base()

# Роли пользователей
class Role(PythonEnum):
    Admin = 'admin'
    User = 'user'

# Сущность пользователей
class Users(Base):
    __tablename__ = 'users'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    full_name = Column(String, nullable=False)  # ФИО
    phone = Column(String, unique=True, nullable=False)  # Телефон (уникальный)
    user_uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)  # UUID пользователя
    role = Column(Enum(Role), nullable=False)  # Роль (admin или user)

    # Связь с корзиной
    cart_items = relationship("Cart", back_populates="user")
    return_requests = relationship("ReturnRequest", back_populates="user")

# Сущность костюмов
class Costumes(Base):
    __tablename__ = 'costumes'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)  # Название костюма
    image_url = Column(String, nullable=False)  # Ссылка на фото
    size = Column(String, nullable=True)  # Размер костюма (опционально)
    costume_uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)  # UUID костюма
    quantity = Column(Integer, default=1)  # Количество костюмов (по умолчанию 1)

    # Связь с корзиной
    cart_items = relationship("Cart", back_populates="costume")
    return_requests = relationship("ReturnRequest", back_populates="costume")

# Сущность корзины (пользователь-костюм)
class Cart(Base):
    __tablename__ = 'cart'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)  # Связь с пользователем
    costume_id = Column(BigInteger, ForeignKey('costumes.id', ondelete='CASCADE'), nullable=False)  # Связь с костюмом
    created_at = Column(DateTime, default=datetime.now, nullable=False)  # Дата создания записи

    # Роли в связи
    user = relationship("Users", back_populates="cart_items")
    costume = relationship("Costumes", back_populates="cart_items")

# Сущность заявок на возврат костюмов
class ReturnRequest(Base):
    __tablename__ = 'return_requests'
    
    id = Column(Integer, primary_key=True)
    request_uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    user_id = Column(BigInteger, ForeignKey('users.id'))
    costume_id = Column(BigInteger, ForeignKey('costumes.id'))
    status = Column(String, default='pending')  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("Users", back_populates="return_requests")
    costume = relationship("Costumes", back_populates="return_requests")

# Уникальные ограничения для таблиц, если необходимо
UniqueConstraint('phone', name='uq_users_phone')
