"""
Основной пакет бота. Здесь мы экспортируем ключевые компоненты,
чтобы их можно было импортировать напрямую из пакета bot.
"""
from .config import BOT_TOKEN, ADMIN_IDS, DATABASE_URL
from .database.models import Advertisement, Photo