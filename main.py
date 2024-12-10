import asyncio
import logging
from os import getenv
from typing import List

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker

from bot.database.models import init_db
from bot.handlers import admin, user
from bot.config import BOT_TOKEN, ADMIN_IDS, DATABASE_URL

# Настраиваем логирование в файл
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Функция для создания сессии базы данных
def get_session():
    engine = init_db(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()

async def main():
    # Инициализируем бота и диспетчер
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрируем роутеры
    dp.include_router(admin.router)
    dp.include_router(user.router)
    
    # Middleware для внедрения сессии БД
    @dp.update.middleware()
    async def database_middleware(handler, event, data):
        session = get_session()
        data["session"] = session
        try:
            return await handler(event, data)
        finally:
            session.close()
    
    # Запускаем бота
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")