from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from datetime import datetime

from ..database.models import Advertisement, Photo
from ..keyboards import admin_kb
from ..utils.states import AdminStates, EditStates
from ..config import ADMIN_IDS
from .user import cmd_start

router = Router()

# Middleware для проверки админских прав
@router.message.middleware()
@router.callback_query.middleware()
async def admin_middleware(handler, event, data):
    user_id = event.from_user.id
    if user_id not in ADMIN_IDS:
        await event.answer("⛔️ У вас нет прав администратора")
        return
    return await handler(event, data)

# Вход в админку
@router.message(Command("admin"))
async def admin_panel(message: Message):
    await message.answer(
        "👑 Панель администратора\n\nВыберите действие из меню ниже:",
        reply_markup=admin_kb.get_admin_main_kb()
    )

# Добавление объявления
@router.message(F.text == "➕ Добавить объявление")
async def start_add_ad(message: Message, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_photos)
    await message.answer(
        "📸 Отправьте фотографии для объявления (можно несколько).\n"
        "После загрузки всех фото нажмите кнопку 'Готово'",
        reply_markup=admin_kb.get_photo_upload_kb()
    )

# Приём фотографий
@router.message(AdminStates.waiting_for_photos, F.photo)
async def process_photos(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await message.answer(
        f"✅ Фото #{len(photos)} загружено! Отправьте ещё или нажмите 'Готово'",
        reply_markup=admin_kb.get_photo_upload_kb()  # Добавляем клавиатуру к каждому сообщению
    )

# Завершение загрузки фото
@router.message(AdminStates.waiting_for_photos, F.text == "Готово")
async def photos_uploaded(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("photos"):
        await message.answer("❌ Нужно загрузить хотя бы одно фото!")
        return
    
    await state.set_state(AdminStates.waiting_for_description)
    await message.answer(
        "📝 Теперь отправьте описание объявления:",
        reply_markup=ReplyKeyboardRemove()  # Вот тут замена!
    )

# Приём описания объявления
@router.message(AdminStates.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    """Обрабатываем полученное описание и запрашиваем цену"""
    await state.update_data(description=message.text)
    await state.set_state(AdminStates.waiting_for_price)
    await message.answer("💰 Укажите цену (только число):")

# Приём цены
@router.message(AdminStates.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    """Проверяем корректность цены и запрашиваем ссылку на менеджера"""
    try:
        price = float(message.text.replace(',', '.'))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Некорректная цена! Введите положительное число:")
        return

    await state.update_data(price=price)
    await state.set_state(AdminStates.waiting_for_manager)
    await message.answer("👤 Отправьте ссылку на менеджера:")

# Приём ссылки на менеджера и предпросмотр
@router.message(AdminStates.waiting_for_manager)
async def process_manager_link(message: Message, state: FSMContext, session: Session):
    """Сохраняем ссылку на менеджера и показываем предпросмотр объявления"""
    await state.update_data(manager_link=message.text)
    data = await state.get_data()

    # Формируем текст предпросмотра
    preview_text = (
        "📋 Предпросмотр объявления:\n\n"
        f"📝 Описание:\n{data['description']}\n\n"
        f"💰 Цена: {data['price']:,.2f} ₽\n\n"
        f"👤 Менеджер: {data['manager_link']}\n\n"
        "Все верно?"
    )

    # Создаем медиа-группу из всех фоток
    media_group = [
        InputMediaPhoto(media=photo_id)
        for photo_id in data['photos'][:-1]  # Берем все фотки кроме последней
    ]
    
    # Добавляем последнюю фотку с текстом описания
    media_group.append(
        InputMediaPhoto(
            media=data['photos'][-1],
            caption=preview_text
        )
    )

    # Отправляем медиа-группу
    sent_messages = await message.answer_media_group(media_group)
    
    # Отправляем кнопки отдельным сообщением
    await message.answer(
        "Выберите действие:",
        reply_markup=admin_kb.get_confirm_kb()
    )

    await state.set_state(AdminStates.confirm_creation)

# Редактирование объявлений
@router.message(F.text == "📝 Редактировать объявление")
async def list_ads_for_edit(message: Message, session: Session):
    """Показываем список объявлений для редактирования"""
    ads = session.scalars(select(Advertisement).order_by(Advertisement.created_at.desc())).all()
    
    if not ads:
        await message.answer("❌ Нет доступных объявлений для редактирования!")
        return

    text = "📝 Выберите объявление для редактирования:\n\n"
    for ad in ads:
        text += f"ID {ad.id}: {ad.description[:50]}...\n"
        text += f"💰 Цена: {ad.price:,.2f} ₽\n\n"

    await message.answer(text, reply_markup=admin_kb.get_ads_list_kb(ads))

# Обработка выбора объявления для редактирования
@router.callback_query(F.data.startswith("edit_ad_"))
async def show_edit_options(callback: CallbackQuery, session: Session):
    """Показываем опции редактирования для выбранного объявления"""
    ad_id = int(callback.data.split('_')[2])
    ad = session.get(Advertisement, ad_id)
    
    if not ad:
        await callback.answer("❌ Объявление не найдено!")
        return

    await callback.message.edit_text(
        f"🔧 Редактирование объявления ID{ad.id}\n"
        f"Текущее описание: {ad.description[:100]}...\n"
        f"Текущая цена: {ad.price:,.2f} ₽\n\n"
        "Выберите, что хотите изменить:",
        reply_markup=admin_kb.get_edit_ad_kb(ad_id)
    )

# Обработчики для каждого типа редактирования
@router.callback_query(F.data.startswith("edit_photos_"))
async def start_edit_photos(callback: CallbackQuery, state: FSMContext):
    """Начинаем редактирование фотографий"""
    ad_id = int(callback.data.split('_')[2])
    await state.update_data(editing_ad_id=ad_id)
    await state.set_state(EditStates.edit_photos)
    
    await callback.message.answer(
        "📸 Отправьте новые фотографии. После загрузки всех фото нажмите 'Готово'",
        reply_markup=admin_kb.get_photo_upload_kb()
    )

# Подтверждение создания
@router.callback_query(AdminStates.confirm_creation, F.data == "confirm")
async def confirm_creation(callback: CallbackQuery, state: FSMContext, session: Session):
    data = await state.get_data()
    
    # Создаём объявление
    ad = Advertisement(
        description=data["description"],
        price=float(data["price"]),
        manager_link=data["manager_link"]
    )
    session.add(ad)
    session.flush()
    
    # Добавляем фотки
    for idx, photo_id in enumerate(data["photos"]):
        photo = Photo(
            advertisement_id=ad.id,
            photo_file_id=photo_id,
            position=idx
        )
        session.add(photo)
    
    session.commit()
    
    await state.clear()
    # Отправляем новое сообщение вместо редактирования
    await callback.message.answer("✅ Объявление успешно создано!")
    # Удаляем предыдущее сообщение с предпросмотром
    await callback.message.delete()
    # Возвращаемся в админку
    await admin_panel(callback.message)

@router.callback_query(AdminStates.confirm_creation, F.data == "cancel")
async def cancel_creation(callback: CallbackQuery, state: FSMContext):
    """Отмена создания объявления"""
    await state.clear()
    await callback.message.delete()  # Удаляем сообщение с предпросмотром
    await callback.message.answer("❌ Создание объявления отменено!")
    await admin_panel(callback.message)  # Возвращаемся в админку

# Удаление объявлений
@router.message(F.text == "❌ Удалить объявление")
async def list_ads_for_delete(message: Message, session: Session):
    """Показываем список объявлений для удаления"""
    ads = session.scalars(select(Advertisement).order_by(Advertisement.created_at.desc())).all()
    
    if not ads:
        await message.answer("❌ Нет доступных объявлений для удаления!")
        return

    text = "🗑 Выберите объявление для удаления:\n\n"
    for ad in ads:
        text += f"ID {ad.id}: {ad.description[:50]}...\n"
        text += f"💰 Цена: {ad.price:,.2f} ₽\n\n"

    await message.answer(text, reply_markup=admin_kb.get_delete_ads_kb(ads))

# Подтверждение удаления
@router.callback_query(F.data.startswith("delete_ad_"))
async def confirm_delete_ad(callback: CallbackQuery, session: Session):
    """Запрашиваем подтверждение удаления"""
    ad_id = int(callback.data.split('_')[2])
    ad = session.get(Advertisement, ad_id)
    
    if not ad:
        await callback.answer("❌ Объявление не найдено!")
        return

    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите удалить объявление ID{ad_id}?\n\n"
        f"Описание: {ad.description[:100]}...\n"
        f"Цена: {ad.price:,.2f} ₽",
        reply_markup=admin_kb.get_delete_confirm_kb(ad_id)
    )

# Финальное удаление
@router.callback_query(F.data.startswith("confirm_delete_"))
async def delete_ad(callback: CallbackQuery, session: Session):
    """Удаляем объявление из базы"""
    ad_id = int(callback.data.split('_')[2])
    ad = session.get(Advertisement, ad_id)
    
    if ad:
        session.delete(ad)
        session.commit()
        await callback.message.edit_text("✅ Объявление успешно удалено!")
    else:
        await callback.answer("❌ Объявление не найдено!")

# Статистика
@router.message(F.text == "📊 Статистика")
async def show_statistics(message: Message, session: Session):
    """Показываем статистику по объявлениям"""
    total_ads = session.scalar(select(func.count()).select_from(Advertisement))
    total_photos = session.scalar(select(func.count()).select_from(Photo))
    
    # Самое дорогое объявление
    most_expensive = session.scalar(
        select(Advertisement)
        .order_by(Advertisement.price.desc())
        .limit(1)
    )
    
    stats_text = (
        "📊 Статистика бота:\n\n"
        f"📝 Всего объявлений: {total_ads}\n"
        f"📸 Всего фотографий: {total_photos}\n"
        f"💰 Самая высокая цена: {most_expensive.price:,.2f} ₽\n" if most_expensive else ""
        f"📅 Последнее обновление: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    
    await message.answer(stats_text)

@router.message(F.text == "Отмена")
async def cancel_action(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await message.answer(
        "❌ Действие отменено", 
        reply_markup=ReplyKeyboardRemove()
    )
    await admin_panel(message)

@router.message(F.text == "🔙 Выход")
async def exit_admin(message: Message):
    """Выход из админ-панели"""
    await message.answer(
        "👋 Выход из панели администратора", 
        reply_markup=ReplyKeyboardRemove()
    )
    # После сообщения о выходе вызываем команду start
    await cmd_start(message)

@router.message(EditStates.edit_photos, F.photo)
async def process_edit_photos(message: Message, state: FSMContext):
    """Обработка новых фото при редактировании"""
    data = await state.get_data()
    photos = data.get("new_photos", [])
    photos.append(message.photo[-1].file_id)
    await state.update_data(new_photos=photos)
    await message.answer(f"✅ Фото #{len(photos)} загружено! Отправьте ещё или нажмите 'Готово'")

@router.message(EditStates.edit_photos, F.text == "Готово")
async def save_edited_photos(message: Message, state: FSMContext, session: Session):
    """Сохранение отредактированных фото"""
    data = await state.get_data()
    if not data.get("new_photos"):
        await message.answer("❌ Нужно загрузить хотя бы одно фото!")
        return
        
    ad_id = data["editing_ad_id"]
    ad = session.get(Advertisement, ad_id)
    
    # Удаляем старые фото
    session.query(Photo).filter(Photo.advertisement_id == ad_id).delete()
    
    # Добавляем новые
    for idx, photo_id in enumerate(data["new_photos"]):
        photo = Photo(
            advertisement_id=ad_id,
            photo_file_id=photo_id,
            position=idx
        )
        session.add(photo)
        
    session.commit()
    await state.clear()
    await message.answer(
        "✅ Фотографии успешно обновлены!", 
        reply_markup=ReplyKeyboardRemove()
    )
    await admin_panel(message)

@router.callback_query(F.data.startswith("edit_desc_"))
async def start_edit_description(callback: CallbackQuery, state: FSMContext):
    """Начинаем редактирование описания"""
    ad_id = int(callback.data.split('_')[2])
    await state.update_data(editing_ad_id=ad_id)
    await state.set_state(EditStates.edit_description)
    
    await callback.message.answer(
        "📝 Отправьте новое описание объявления:", 
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отмена")]], 
            resize_keyboard=True
        )
    )

@router.message(EditStates.edit_description)
async def save_edited_description(message: Message, state: FSMContext, session: Session):
    """Сохраняем новое описание"""
    data = await state.get_data()
    ad_id = data["editing_ad_id"]
    ad = session.get(Advertisement, ad_id)
    
    if ad:
        ad.description = message.text
        session.commit()
        await state.clear()
        await message.answer(
            "✅ Описание успешно обновлено!", 
            reply_markup=ReplyKeyboardRemove()
        )
        await admin_panel(message)

@router.callback_query(F.data.startswith("edit_price_"))
async def start_edit_price(callback: CallbackQuery, state: FSMContext):
    """Начинаем редактирование цены"""
    ad_id = int(callback.data.split('_')[2])
    await state.update_data(editing_ad_id=ad_id)
    await state.set_state(EditStates.edit_price)
    
    await callback.message.answer(
        "💰 Укажите новую цену (только число):",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отмена")]], 
            resize_keyboard=True
        )
    )

@router.message(EditStates.edit_price)
async def save_edited_price(message: Message, state: FSMContext, session: Session):
    """Сохраняем новую цену"""
    try:
        price = float(message.text.replace(',', '.'))
        if price <= 0:
            raise ValueError
            
        data = await state.get_data()
        ad_id = data["editing_ad_id"]
        ad = session.get(Advertisement, ad_id)
        
        if ad:
            ad.price = price
            session.commit()
            await state.clear()
            await message.answer(
                "✅ Цена успешно обновлена!", 
                reply_markup=ReplyKeyboardRemove()
            )
            await admin_panel(message)
    except ValueError:
        await message.answer("❌ Некорректная цена! Введите положительное число:")

@router.callback_query(F.data.startswith("edit_manager_"))
async def start_edit_manager(callback: CallbackQuery, state: FSMContext):
    """Начинаем редактирование ссылки на менеджера"""
    ad_id = int(callback.data.split('_')[2])
    await state.update_data(editing_ad_id=ad_id)
    await state.set_state(EditStates.edit_manager)
    
    await callback.message.answer(
        "👤 Отправьте новую ссылку на менеджера:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отмена")]], 
            resize_keyboard=True
        )
    )

@router.message(EditStates.edit_manager)
async def save_edited_manager(message: Message, state: FSMContext, session: Session):
    """Сохраняем новую ссылку на менеджера"""
    data = await state.get_data()
    ad_id = data["editing_ad_id"]
    ad = session.get(Advertisement, ad_id)
    
    if ad:
        ad.manager_link = message.text
        session.commit()
        await state.clear()
        await message.answer(
            "✅ Контакт менеджера успешно обновлен!", 
            reply_markup=ReplyKeyboardRemove()
        )
        await admin_panel(message)

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню админки"""
    await state.clear()
    await callback.message.delete()
    await admin_panel(callback.message)