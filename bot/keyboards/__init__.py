"""
Пакет с клавиатурами бота.
Экспортируем функции создания клавиатур для админов и пользователей.
"""
from .admin_kb import (
    get_admin_main_kb,
    get_photo_upload_kb,
    get_confirm_kb,
    get_edit_ad_kb,
    get_ads_list_kb,
    get_delete_ads_kb,
    get_delete_confirm_kb
)
from .user_kb import get_navigation_kb, get_start_kb