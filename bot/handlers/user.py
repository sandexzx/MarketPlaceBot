from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from ..database.models import Advertisement, Photo
from ..keyboards import user_kb
from ..utils import messages

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    """
    Обработчик команды /start
    Показывает приветственное сообщение и кнопку для начала просмотра
    """
    await message.answer(
        messages.WELCOME_MESSAGE,
        reply_markup=user_kb.get_start_kb()
    )

@router.callback_query(F.data == "show_ads")
async def show_first_ad(callback: CallbackQuery, session: Session):
    """
    Показывает первое доступное объявление
    Добавляет кнопки навигации и контакта с менеджером
    """
    # Получаем первое объявление
    query = select(Advertisement).order_by(Advertisement.created_at.desc())
    ad = session.scalar(query)
    
    if not ad:
        await callback.message.edit_text(
            messages.NO_ADS_MESSAGE,
            reply_markup=None
        )
        return

    # Получаем общее количество объявлений для навигации
    total_ads = session.scalar(select(func.count()).select_from(Advertisement))
    
    # Формируем сообщение с объявлением
    await show_advertisement(
        callback.message,
        ad,
        session,
        current_position=1,
        total_ads=total_ads,
        edit=True
    )

async def show_advertisement(message, ad, session, current_position, total_ads, edit=False):
    """
    Вспомогательная функция для отображения объявления
    Загружает фотографии, формирует описание и добавляет кнопки
    """
    # Получаем все фото объявления, отсортированные по позиции
    photos = session.scalars(
        select(Photo)
        .where(Photo.advertisement_id == ad.id)
        .order_by(Photo.position)
    ).all()
    
    # Если больше одной фотографии - создаём медиагруппу
    if len(photos) > 1:
        media_group = [
            InputMediaPhoto(media=photo.photo_file_id)
            for photo in photos
        ]
        # Добавляем подпись к последнему фото
        media_group[-1].caption = format_ad_description(ad)
        
        if edit:
            # Удаляем предыдущее сообщение
            await message.delete()
            message = message.chat
            
        await message.send_media_group(media_group)
        
        # Отправляем кнопки навигации отдельным сообщением
        await message.answer(
            "Используйте кнопки ниже для навигации:",
            reply_markup=user_kb.get_navigation_kb(current_position, total_ads)
        )
    else:
        # Если фото одно - отправляем одним сообщением с кнопками
        if edit:
            await message.edit_media(
                InputMediaPhoto(
                    media=photos[0].photo_file_id,
                    caption=format_ad_description(ad)
                ),
                reply_markup=user_kb.get_navigation_kb(current_position, total_ads)
            )
        else:
            await message.answer_photo(
                photos[0].photo_file_id,
                caption=format_ad_description(ad),
                reply_markup=user_kb.get_navigation_kb(current_position, total_ads)
            )

def format_ad_description(ad: Advertisement) -> str:
    """
    Форматирует описание объявления с эмодзи и разметкой
    """
    return (
        f"📝 Описание:\n"
        f"{ad.description}\n\n"
        f"💰 Цена: {ad.price:,.2f} ₽\n"
    )

@router.callback_query(F.data.startswith(("next_", "prev_")))
async def navigate_ads(callback: CallbackQuery, session: Session):
    """
    Обработчик навигации по объявлениям
    Показывает следующее/предыдущее объявление
    """
    action, current_id = callback.data.split("_")
    current_id = int(current_id)
    
    # Определяем направление навигации
    if action == "next":
        query = select(Advertisement).where(Advertisement.id > current_id).order_by(Advertisement.id)
    else:
        query = select(Advertisement).where(Advertisement.id < current_id).order_by(Advertisement.id.desc())
    
    next_ad = session.scalar(query)
    if not next_ad:
        await callback.answer("Больше объявлений нет! 🤷‍♂️")
        return
        
    # Получаем общее количество объявлений
    total_ads = session.scalar(select(func.count()).select_from(Advertisement))
    
    # Определяем текущую позицию
    current_position = session.scalar(
        select(func.count())
        .select_from(Advertisement)
        .where(Advertisement.id <= next_ad.id)
    )
    
    await show_advertisement(
        callback.message,
        next_ad,
        session,
        current_position,
        total_ads,
        edit=True
    )

@router.callback_query(F.data.startswith("rent_"))
async def rent_ad(callback: CallbackQuery, session: Session):
    """
    Обработчик кнопки "Арендовать"
    Показывает контакт менеджера
    """
    ad_id = int(callback.data.split("_")[1])
    ad = session.get(Advertisement, ad_id)
    
    if not ad:
        await callback.answer("Это объявление уже удалено! 😢")
        return
        
    await callback.message.answer(
        f"👤 Для аренды свяжитесь с менеджером:\n{ad.manager_link}"
    )