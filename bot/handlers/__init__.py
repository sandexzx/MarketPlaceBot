"""
Пакет обработчиков сообщений.
Экспортируем роутеры для администраторов и пользователей.
"""
from .admin import router as admin_router
from .user import router as user_router