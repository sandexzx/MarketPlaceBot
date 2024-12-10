from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Boolean

Base = declarative_base()

class Advertisement(Base):
    __tablename__ = 'advertisements'
    
    id = Column(Integer, primary_key=True)
    description = Column(String, nullable=False)
    price = Column(String, nullable=False)
    manager_link = Column(String, nullable=True)  # Делаем nullable, т.к. у рекламных объявлений не будет менеджера
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_promotional = Column(Boolean, default=False)  # Новое поле для отметки рекламных объявлений
    views_count = Column(Integer, default=0)  # Количество показов
    last_shown = Column(DateTime, nullable=True)  # Время последнего показа
    
    # Связь с фотографиями
    photos = relationship("Photo", back_populates="advertisement", cascade="all, delete-orphan")

class Photo(Base):
    __tablename__ = 'photos'
    
    id = Column(Integer, primary_key=True)
    advertisement_id = Column(Integer, ForeignKey('advertisements.id'))
    photo_file_id = Column(String, nullable=False)
    position = Column(Integer, nullable=False)
    
    # Обратная связь с объявлением
    advertisement = relationship("Advertisement", back_populates="photos")

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)  # Телеграм юзернейм
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    notifications_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def generate_promo_id() -> int:
    """Генерирует ID для рекламного объявления, начинающийся с 9"""
    return int('9' + str(int(datetime.utcnow().timestamp()))[-6:])

# Функция для инициализации БД
def init_db(database_url: str):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine