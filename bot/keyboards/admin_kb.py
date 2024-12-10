from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List
from ..database.models import Advertisement

def get_admin_main_kb() -> ReplyKeyboardMarkup:
    """Главное админское меню"""
    keyboard = [
        [
            KeyboardButton(text="➕ Добавить объявление"),
            KeyboardButton(text="📢 Добавить рекламу")
        ],
        [
            KeyboardButton(text="📝 Редактировать объявление"),
            KeyboardButton(text="❌ Удалить объявление")
        ],
        [
            KeyboardButton(text="📊 Статистика"),
            KeyboardButton(text="🔙 Выход")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_photo_upload_kb() -> ReplyKeyboardMarkup:
    """Клава для загрузки фоток"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Готово")], [KeyboardButton(text="Отмена")]],
        resize_keyboard=True
    )

def get_confirm_kb() -> InlineKeyboardMarkup:
    """Клава подтверждения действий"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Сохранить", callback_data="confirm"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_edit_ad_kb(ad_id: int) -> InlineKeyboardMarkup:
    """Клава для редактирования конкретного объявления"""
    keyboard = [
        [InlineKeyboardButton(text="📸 Изменить фото", callback_data=f"edit_photos_{ad_id}")],
        [InlineKeyboardButton(text="📝 Изменить описание", callback_data=f"edit_desc_{ad_id}")],
        [InlineKeyboardButton(text="💰 Изменить цену", callback_data=f"edit_price_{ad_id}")],
        [InlineKeyboardButton(text="👤 Изменить менеджера", callback_data=f"edit_manager_{ad_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_ads_list_kb(ads: List[Advertisement]) -> InlineKeyboardMarkup:
    """Клавиатура со списком объявлений"""
    keyboard = [
        [InlineKeyboardButton(
            text=f"ID{ad.id}: {ad.description[:20]}...", 
            callback_data=f"edit_ad_{ad.id}"
        )]
        for ad in ads
    ]
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_delete_ads_kb(ads: List[Advertisement]) -> InlineKeyboardMarkup:
    """Клавиатура для удаления объявлений"""
    keyboard = [
        [InlineKeyboardButton(
            text=f"❌ ID{ad.id}: {ad.description[:20]}...", 
            callback_data=f"delete_ad_{ad.id}"
        )]
        for ad in ads
    ]
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_delete_confirm_kb(ad_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{ad_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_admin")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)