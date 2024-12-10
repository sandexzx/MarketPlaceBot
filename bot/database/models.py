from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Advertisement(Base):
    __tablename__ = 'advertisements'
    
    id = Column(Integer, primary_key=True)
    description = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    manager_link = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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

# Функция для инициализации БД
def init_db(database_url: str):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine