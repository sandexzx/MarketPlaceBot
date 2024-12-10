from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_navigation_kb(current_ad_id: int, total_ads: int) -> InlineKeyboardMarkup:
    """Клавиатура навигации по объявлениям"""
    buttons = []
    
    # Кнопки навигации
    nav_buttons = []
    if current_ad_id > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"prev_{current_ad_id}"))
    if current_ad_id < total_ads:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"next_{current_ad_id}"))
    buttons.append(nav_buttons)
    
    # Кнопка связи с менеджером
    buttons.append([InlineKeyboardButton(text="📞 Арендовать", callback_data=f"rent_{current_ad_id}")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_start_kb() -> InlineKeyboardMarkup:
    """Стартовая клавиатура"""
    keyboard = [[InlineKeyboardButton(text="🏠 Смотреть объявления", callback_data="show_ads")]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)