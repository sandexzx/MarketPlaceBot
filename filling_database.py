import os
import random
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from bot.database.models import Advertisement, Photo, Base
from bot.config import DATABASE_URL, MEDIA_DIR, BOT_TOKEN, ADMIN_IDS
from aiogram import Bot
import logging
from aiogram.types import FSInputFile
from datetime import UTC 

# Примеры описаний для обычных объявлений
DESCRIPTIONS = [
    "Уютная однокомнатная квартира в центре города. Свежий ремонт, вся необходимая мебель и техника. Рядом метро, магазины, парк.",
    "Просторная двухкомнатная квартира с панорамным видом. Современный дизайнерский ремонт, встроенная кухня, кондиционер.",
    "Светлая студия в новом ЖК. Качественная отделка, мебель, бытовая техника. Закрытая территория, подземный паркинг.",
    "Комфортабельная трехкомнатная квартира в тихом районе. Раздельные комнаты, два санузла, гардеробная.",
    "Стильная квартира-студия с террасой. Панорамные окна, современная мебель, вся техника. Охраняемая территория."
]

# Примеры описаний для рекламных объявлений
PROMO_DESCRIPTIONS = [
    "🌟 СПЕЦИАЛЬНОЕ ПРЕДЛОЖЕНИЕ! Первый месяц аренды со скидкой 50%! Успейте забронировать квартиру мечты!",
    "🎉 АКЦИЯ! При длительной аренде – бесплатная уборка каждый месяц! Только качественное жилье от надежного агентства!",
    "⭐️ ЭКСКЛЮЗИВ! VIP-апартаменты в историческом центре. Дизайнерский ремонт, панорамные окна, терраса.",
    "💫 ГОРЯЧЕЕ ПРЕДЛОЖЕНИЕ! Новый ЖК бизнес-класса. Первым арендаторам – месяц бесплатного фитнеса!",
    "🏆 ПРЕМИУМ-КВАРТИРЫ в элитном доме! Специальные условия для долгосрочной аренды. Количество предложений ограничено!"
]

# Ценовые диапазоны (в формате строк для более гибкого отображения)
PRICES = [
    "45.000₽/месяц",
    "60.000₽/месяц",
    "75.000₽/месяц",
    "85.000₽/месяц",
    "120.000₽/месяц"
]

# Контакты менеджеров
MANAGERS = [
    "@rental_manager_anna",
    "@rental_expert_mike",
    "@home_finder_kate",
    "@property_pro_alex",
    "@rent_master_maria"
]

def get_random_images(num_images):
    """Получает случайные изображения из директории media"""
    image_files = list(Path(MEDIA_DIR).glob("*.PNG"))
    if not image_files:
        raise Exception(f"No PNG images found in {MEDIA_DIR}")
    
    # Выбираем случайные файлы, может повторяться
    selected_images = random.choices(image_files, k=num_images)
    return [str(img) for img in selected_images]

async def upload_photo_to_telegram(bot: Bot, photo_path: str) -> str:
    """Загружает фото в Telegram и возвращает file_id"""
    try:
        # Создаем FSInputFile из пути к файлу
        photo = FSInputFile(photo_path)
        result = await bot.send_photo(
            chat_id=ADMIN_IDS[0],  # Отправляем первому админу
            photo=photo
        )
        # Сразу удаляем сообщение, нам нужен только file_id
        await bot.delete_message(
            chat_id=ADMIN_IDS[0],
            message_id=result.message_id
        )
        return result.photo[-1].file_id
    except Exception as e:
        logging.error(f"Ошибка при загрузке фото {photo_path}: {e}")
        raise


async def create_regular_ad(bot: Bot, session, created_at=None):
    """Создает обычное объявление с случайными данными"""
    description = random.choice(DESCRIPTIONS)
    price = random.choice(PRICES)
    manager = random.choice(MANAGERS)
    
    ad = Advertisement(
        description=description,
        price=price,
        manager_link=manager,
        is_promotional=False,
        created_at=created_at or datetime.utcnow(),
        views_count=0,  # Начальное количество просмотров
        last_shown=None  # Время последнего просмотра изначально 
    )
    session.add(ad)
    session.flush()
    
    # Загружаем 2-4 фотографии в Telegram
    images = get_random_images(random.randint(2, 4))
    for idx, image_path in enumerate(images):
        file_id = await upload_photo_to_telegram(bot, image_path)
        photo = Photo(
            advertisement_id=ad.id,
            photo_file_id=file_id,
            position=idx
        )
        session.add(photo)
    
    return ad

async def create_promo_ad(bot: Bot, session, created_at=None):
    """Создает рекламное объявление"""
    description = random.choice(PROMO_DESCRIPTIONS)
    
    ad = Advertisement(
        description=description,
        price="РЕКЛАМНОЕ ПРЕДЛОЖЕНИЕ",
        manager_link="",
        is_promotional=True,
        created_at=created_at or datetime.utcnow(),
        views_count=0,  # Начальное количество просмотров
        last_shown=None  # Время последнего просмотра изначально 
    )
    session.add(ad)
    session.flush()
    
    # Загружаем 3-5 фотографий в Telegram
    images = get_random_images(random.randint(3, 5))
    for idx, image_path in enumerate(images):
        file_id = await upload_photo_to_telegram(bot, image_path)
        photo = Photo(
            advertisement_id=ad.id,
            photo_file_id=file_id,
            position=idx
        )
        session.add(photo)
    
    return ad

async def populate_database():
    """Заполняет базу данных тестовыми данными"""
    # Инициализируем подключение к БД и бота
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    bot = Bot(token=BOT_TOKEN)
    
    try:
        # Очищаем существующие данные
        session.query(Photo).delete()
        session.query(Advertisement).delete()
        
        print("Начинаем заполнение базы данных...")
        
        # Создаем обычные объявления с разными датами
        base_date = datetime.now(UTC) - timedelta(days=30)
        for i in range(20):
            created_at = base_date + timedelta(days=i)
            print(f"Создаю обычное объявление {i+1}/20...")
            await create_regular_ad(bot, session, created_at)
            session.commit()  # Коммитим после каждого объявления
        
        # Создаем рекламные объявления
        for i in range(5):
            print(f"Создаю рекламное объявление {i+1}/5...")
            await create_promo_ad(bot, session)
            session.commit()  # Коммитим после каждого объявления
        
        print("База данных успешно заполнена тестовыми данными!")
        print(f"Создано обычных объявлений: 20")
        print(f"Создано рекламных объявлений: 5")
        
    except Exception as e:
        session.rollback()
        print(f"Ошибка при заполнении базы данных: {e}")
        raise
    finally:
        session.close()
        await bot.session.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(populate_database())