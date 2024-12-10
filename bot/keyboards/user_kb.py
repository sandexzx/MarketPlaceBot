from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_navigation_kb(current_position: int, total_ads: int, ad_id: int) -> InlineKeyboardMarkup:
    """Клавиатура навигации по объявлениям с использованием реального ad_id."""
    buttons = []
    
    nav_buttons = []
    # Используем ad_id в callback_data
    if current_position > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"prev_{ad_id}"))
    if current_position < total_ads:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"next_{ad_id}"))
    buttons.append(nav_buttons)
    
    # Для аренды тоже используем ad_id
    buttons.append([InlineKeyboardButton(text="📞 Арендовать", callback_data=f"rent_{ad_id}")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_start_kb() -> InlineKeyboardMarkup:
    """Стартовая клавиатура"""
    keyboard = [[InlineKeyboardButton(text="🏠 Смотреть объявления", callback_data="show_ads")]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)