from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..database.models import User, Advertisement
import logging
from datetime import datetime
from ..config import ADMIN_IDS

async def notify_new_ad(bot: Bot, session: Session, ad: Advertisement):
    """
    Отправляет минималистичное уведомление о новом объявлении 
    с кнопкой для просмотра и ведёт подробный лог отправки
    """
    logging.info(f"Starting notification process for ad ID: {ad.id}")
    
    users = session.scalars(
    select(User).where(
        (User.notifications_enabled == True) & # noqa: E712
        (User.telegram_id.notin_(ADMIN_IDS))
    )
).all()
    
    logging.info(f"Found {len(users)} users with enabled notifications")
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="🏠 Смотреть", callback_data=f"view_ad_{ad.id}")
        ]]
    )
    
    message_text = "Привет! У нас новое объявление! 🏠"

    successful_sends = 0
    failed_sends = 0
    
    for user in users:
        try:
            await bot.send_message(
                user.telegram_id,
                message_text,
                reply_markup=keyboard
            )
            logging.info(f"Successfully sent notification to user {user.telegram_id} "
                        f"(username: {user.username or 'None'}) "
                        f"for ad ID: {ad.id}")
            successful_sends += 1
            
            # Обновляем время последней активности пользователя
            user.last_activity = datetime.utcnow()
            session.commit()
            
        except Exception as e:
            failed_sends += 1
            logging.error(f"Failed to send notification to user {user.telegram_id}: {str(e)}")
            
            # Если пользователь заблокировал бота, отключаем уведомления
            if "Forbidden: bot was blocked by the user" in str(e):
                logging.info(f"User {user.telegram_id} blocked bot, disabling notifications")
                user.notifications_enabled = False
                session.commit()
    
    logging.info(f"Notification summary for ad ID {ad.id}:")
    logging.info(f"- Successfully sent: {successful_sends}")
    logging.info(f"- Failed to send: {failed_sends}")