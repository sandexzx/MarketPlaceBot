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
    # Получаем все ID объявлений, отсортированные по дате создания
    query = select(Advertisement).order_by(Advertisement.created_at.desc())
    ads = session.scalars(query).all()
    
    if not ads:  # Проверяем, пуст ли список ads
        # Удаляем старое сообщение с кнопкой
        await callback.message.delete()
        # Отправляем новое сообщение
        await callback.message.answer(
            messages.NO_ADS_MESSAGE,
            reply_markup=user_kb.get_start_kb()
        )
        return

    # Показываем первое объявление
    await show_advertisement(
        callback.message,
        ads[0],
        session,
        current_position=1,
        total_ads=len(ads),
        edit=True
    )

async def show_advertisement(message, ad, session, current_position, total_ads, edit=False):
    """
    Вспомогательная функция для отображения объявления.
    Загружает фотографии, формирует описание и добавляет кнопки навигации.
    Использует реальный ad.id для корректной навигации.
    """
    # Получаем все фото объявления, отсортированные по позиции
    photos = session.scalars(
        select(Photo)
        .where(Photo.advertisement_id == ad.id)
        .order_by(Photo.position)
    ).all()
    
    # Если у объявления нет фотографий
    if not photos:
        await message.answer(
            f"⚠️ Ошибка: у объявления нет фотографий!\n\n{format_ad_description(ad)}",
            reply_markup=user_kb.get_navigation_kb(current_position, total_ads, ad.id)
        )
        return
    
    # Формируем клавиатуру навигации с использованием реального ad.id
    navigation_kb = user_kb.get_navigation_kb(current_position, total_ads, ad.id)

    # Если фото только одно
    if len(photos) == 1:
        if edit:
            await message.delete()
            await message.bot.send_photo(
                chat_id=message.chat.id,
                photo=photos[0].photo_file_id,
                caption=format_ad_description(ad),
                reply_markup=navigation_kb
            )
        else:
            await message.answer_photo(
                photo=photos[0].photo_file_id,
                caption=format_ad_description(ad),
                reply_markup=navigation_kb
            )
    else:
        # Если фото несколько
        media_group = [
            InputMediaPhoto(media=photo.photo_file_id)
            for photo in photos
        ]
        # Добавляем описание к последнему фото
        media_group[-1].caption = format_ad_description(ad)
        
        if edit:
            await message.delete()
            bot = message.bot
            # Отправляем медиагруппу
            await bot.send_media_group(chat_id=message.chat.id, media=media_group)
            # Отдельным сообщением отправляем кнопки навигации
            await bot.send_message(
                chat_id=message.chat.id,
                text="Используйте кнопки ниже для навигации:",
                reply_markup=navigation_kb
            )
        else:
            await message.answer_media_group(media_group)
            await message.answer(
                "Используйте кнопки ниже для навигации:",
                reply_markup=navigation_kb
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
    action, ad_id_str = callback.data.split("_")
    ad_id = int(ad_id_str)
    
    # Получаем отсортированный список объявлений
    query = select(Advertisement).order_by(Advertisement.created_at.desc())
    ads = session.scalars(query).all()
    
    if not ads:
        await callback.answer("Объявлений нет! 🤷‍♂️")
        return

    # Находим индекс объявления с текущим ad_id
    current_index = next((i for i, ad in enumerate(ads) if ad.id == ad_id), None)
    
    if current_index is None:
        # Если объявление не найдено (могло быть удалено), показываем первое, если есть
        if ads:
            await show_advertisement(
                callback.message,
                ads[0],
                session,
                current_position=1,
                total_ads=len(ads),
                edit=True
            )
        return
    
    if action == "next":
        next_index = current_index + 1
        if next_index >= len(ads):
            await callback.answer("Это последнее объявление! 🤷‍♂️")
            return
    else:  # prev
        next_index = current_index - 1
        if next_index < 0:
            await callback.answer("Это первое объявление! 🤷‍♂️")
            return

    # Переходим к следущему/предыдущему объявлению
    await show_advertisement(
        callback.message,
        ads[next_index],
        session,
        current_position=next_index + 1,
        total_ads=len(ads),
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