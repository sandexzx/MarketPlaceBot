from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from datetime import datetime
from pathlib import Path
from aiogram.types import FSInputFile
import logging
import random
from sqlalchemy import or_
from aiogram.fsm.context import FSMContext
from ..utils.states import UserStates


from ..database.models import Advertisement, Photo
from ..keyboards import user_kb
from ..utils import messages
from ..database.models import User
from ..config import WELCOME_IMAGE


router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, session: Session):
    """
    Обработчик команды /start
    Регистрирует пользователя и показывает приветственное сообщение с картинкой
    """
    # Сохраняем информацию о пользователе
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    if not user:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        session.add(user)
        session.commit()
    
    try:
        # Проверяем существование картинки
        if Path(WELCOME_IMAGE).exists():
            # Отправляем картинку с подписью
            await message.answer_photo(
                photo=FSInputFile(WELCOME_IMAGE),
                caption=messages.WELCOME_MESSAGE,
                reply_markup=user_kb.get_start_kb()
            )
        else:
            # Если картинки нет, отправляем просто текст
            await message.answer(
                messages.WELCOME_MESSAGE,
                reply_markup=user_kb.get_start_kb()
            )
    except Exception as e:
        logging.error(f"Ошибка при отправке приветственного сообщения: {e}")
        # В случае ошибки отправляем сообщение без картинки
        await message.answer(
            messages.WELCOME_MESSAGE,
            reply_markup=user_kb.get_start_kb()
        )


@router.callback_query(F.data == "show_ads")
async def show_first_ad(callback: CallbackQuery, session: Session, state: FSMContext):
    """
    Показывает первое доступное объявление
    Добавляет кнопки навигации и контакта с менеджером
    """
    # Получаем только обычные объявления
    query = select(Advertisement).where(Advertisement.is_promotional == False).order_by(Advertisement.created_at.desc())
    ads = session.scalars(query).all()
    
    if not ads:
        await callback.message.delete()
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

    # Переходим в состояние просмотра объявлений и сохраняем текущий индекс
    # Первый элемент в списке ads соответствует индексу 0
    await state.set_state(UserStates.viewing_ads)
    await state.update_data(current_index=0, total_ads=len(ads))

async def show_advertisement(message, ad, session, current_position, total_ads, edit=False):
    """
    Вспомогательная функция для отображения объявления.
    Загружает фотографии, формирует описание и добавляет кнопки навигации.
    Использует реальный ad.id для корректной навигации.
    """

    # Увеличиваем счетчик просмотров
    ad.views_count += 1
    ad.last_shown = datetime.utcnow()
    session.commit()

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
    navigation_kb = user_kb.get_navigation_kb(current_position, total_ads, ad.id, ad.is_promotional)

    # Если фото только одно
    if len(photos) == 1:
        # Если фото только одно
        if len(photos) == 1:
            if edit:
                await message.delete()
                await message.bot.send_photo(
                    chat_id=message.chat.id,
                    photo=photos[0].photo_file_id,
                    caption=format_ad_description(ad),
                    parse_mode='Markdown'
                )

                await message.bot.send_message(
                    chat_id=message.chat.id,
                    text="Используйте кнопки ниже для навигации:",
                    reply_markup=navigation_kb
                )
            else:
                await message.answer_photo(
                    photo=photos[0].photo_file_id,
                    caption=format_ad_description(ad)
                )
                await message.answer(
                    "Используйте кнопки ниже для навигации:",
                    reply_markup=navigation_kb
                )
    else:
        # Если фото несколько
        media_group = [
            InputMediaPhoto(media=photo.photo_file_id)
            for photo in photos
        ]
        # Добавляем описание к последнему фото
        media_group[-1] = InputMediaPhoto(
            media=media_group[-1].media,
            caption=format_ad_description(ad),
            parse_mode='Markdown'
        )

        if edit:
            await message.delete()
            bot = message.bot
            await bot.send_media_group(chat_id=message.chat.id, media=media_group)
            await bot.send_message(
                chat_id=message.chat.id,
                text="Используйте кнопки ниже для навигации:",
                reply_markup=navigation_kb,
                parse_mode='Markdown'
            )
        else:
            await message.answer_media_group(media_group)
            await message.answer(
                "Используйте кнопки ниже для навигации:",
                reply_markup=navigation_kb,
                parse_mode='Markdown'
            )


def format_ad_description(ad: Advertisement) -> str:
    """
    Форматирует описание объявления с учётом типа (обычное/рекламное)
    """
    if ad.is_promotional:
        return f"📢 РЕКЛАМА\n\n{ad.description}"
    else:
        return (
            f"📝 Описание:\n{ad.description}\n\n"
            f"💰 Цена: {ad.price}\n"
        )

@router.callback_query(F.data.startswith(("next_", "prev_")))
async def navigate_ads(callback: CallbackQuery, session: Session, state: FSMContext):
    """
    Обработчик навигации по объявлениям
    Показывает следующее/предыдущее объявление с шансом показа рекламы
    """
    action, ad_id_str = callback.data.split("_")
    ad_id = int(ad_id_str)

    data = await state.get_data()
    current_index = data.get("current_index", 0)
    total_ads = data.get("total_ads", 0)

    # Получаем все обычные объявления
    regular_ads = session.scalars(
        select(Advertisement)
        .where(Advertisement.is_promotional == False)
        .order_by(Advertisement.created_at.desc())
    ).all()

    # Получаем все рекламные объявления
    promo_ads = session.scalars(
        select(Advertisement)
        .where(Advertisement.is_promotional == True)
        .order_by(Advertisement.created_at.desc())
    ).all()

    # Находим текущее объявление по индексу
    # Если число объявлений изменилось, проверим актуальность current_index
    if current_index >= len(regular_ads):
        # Если текущий индекс вне диапазона (например, объявления удалили),
        # сбрасываем позицию на 0
        current_index = 0

    # Если нет обычных объявлений
    if not regular_ads:
        await callback.answer("Объявлений нет! 🤷‍♂️")
        return

    # Двигаем индекс в зависимости от действия
    if action == "next":
        # Проверяем, не достигли ли конца
        if current_index < len(regular_ads) - 1:
            current_index += 1
        else:
            await callback.answer("Это последнее объявление! 🤷‍♂️")
            return
    else:  # prev
        if current_index > 0:
            current_index -= 1
        else:
            await callback.answer("Это первое объявление! 🤷‍♂️")
            return

    # С вероятностью 20% показываем рекламное объявление при переходе вперед,
    # но только если действие "next"
    show_promo = (action == "next") and (random.random() < 0.2) and promo_ads

    if show_promo:
        # Показываем случайное рекламное объявление
        ad_to_show = random.choice(promo_ads)
        # Откатываем индекс назад, т.к. после рекламы должно показаться следующее обычное объявление
        if action == "next":
            current_index -= 1  # Компенсируем increment, который был сделан ранее
    else:
        # Показываем очередное обычное объявление по текущему индексу
        ad_to_show = regular_ads[current_index]

    # Отображаем выбранное объявление
    await show_advertisement(
        callback.message,
        ad_to_show,
        session,
        current_position=(current_index + 1),
        total_ads=len(regular_ads),
        edit=True
    )

    # Сохраняем обновленный индекс и общее количество объявлений
    await state.update_data(current_index=current_index, total_ads=len(regular_ads))


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

@router.message(Command("notifications"))
async def toggle_notifications(message: Message, session: Session):
    """Включение/выключение уведомлений"""
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    if not user:
        return
        
    user.notifications_enabled = not user.notifications_enabled
    session.commit()
    
    status = "включены ✅" if user.notifications_enabled else "выключены ❌"
    await message.answer(f"Уведомления о новых объявлениях {status}")

@router.message(Command("ads"))
async def cmd_ads(message: Message, session: Session):
    """
    Обработчик команды /ads
    Показывает доступные объявления
    """
    # Получаем все объявления, отсортированные по дате создания
    query = select(Advertisement).order_by(Advertisement.created_at.desc())
    ads = session.scalars(query).all()
    
    if not ads:
        await message.answer(
            messages.NO_ADS_MESSAGE,
            reply_markup=user_kb.get_start_kb()
        )
        return
        
    # Показываем первое объявление
    await show_advertisement(
        message,
        ads[0],
        session,
        current_position=1,
        total_ads=len(ads)
    )

@router.callback_query(F.data.startswith("view_ad_"))
async def view_specific_ad(callback: CallbackQuery, session: Session):
    """
    Показывает конкретное объявление по ID из уведомления
    """
    ad_id = int(callback.data.split("_")[2])
    
    # Получаем объявление по ID
    ad = session.get(Advertisement, ad_id)
    if not ad:
        await callback.answer("Упс! Похоже, это объявление уже удалено 😢")
        # Показываем первое доступное объявление
        await show_first_ad(callback, session)
        return
        
    # Получаем общее количество объявлений для навигации
    total_ads = session.scalar(select(func.count()).select_from(Advertisement))
    
    # Определяем позицию текущего объявления
    current_position = session.scalar(
        select(func.count())
        .select_from(Advertisement)
        .where(Advertisement.created_at >= ad.created_at)
    )
    
    # Показываем запрошенное объявление
    await show_advertisement(
        callback.message,
        ad,
        session,
        current_position=current_position,
        total_ads=total_ads,
        edit=True
    )