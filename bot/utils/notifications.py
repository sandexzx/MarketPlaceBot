from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..database.models import User, Advertisement

async def notify_new_ad(bot: Bot, session: Session, ad: Advertisement):
    """
    Отправляет минималистичное уведомление о новом объявлении 
    с кнопкой для просмотра
    """
    # Получаем пользователей с включенными уведомлениями
    users = session.scalars(
        select(User).where(User.notifications_enabled == True)  # noqa: E712
    ).all()
    
    # Создаём инлайн-клавиатуру с кнопкой
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="🏠 Смотреть", callback_data="show_ads")
        ]]
    )
    
    message_text = "Привет! У нас новое объявление! 🏠"
    
    # Отправляем уведомления с кнопкой
    for user in users:
        try:
            await bot.send_message(
                user.telegram_id,
                message_text,
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Ошибка отправки уведомления пользователю {user.telegram_id}: {e}")