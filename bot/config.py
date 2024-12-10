import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv(override=True)

# Определяем базовую директорию проекта
BASE_DIR = Path(__file__).resolve().parent.parent

# Путь к файлу базы данных
DB_FILE = BASE_DIR / "data" / "bot.db"

def get_admin_ids() -> List[int]:
    """
    Получает список ID администраторов из переменной окружения ADMIN_IDS.
    Поддерживает как один ID, так и несколько через запятую.
    
    Returns:
        List[int]: Список ID администраторов
    """
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    if not admin_ids_str:
        raise ValueError("ADMIN_IDS не указаны в .env файле!")
    
    try:
        # Убираем комментарии, если они есть (всё после #)
        admin_ids_str = admin_ids_str.split('#')[0].strip()
        
        # Если в строке есть запятая - разбиваем по ней
        if ',' in admin_ids_str:
            admin_ids = [int(id_.strip()) for id_ in admin_ids_str.split(",") if id_.strip()]
        else:
            # Если запятой нет - просто преобразуем строку в число
            admin_ids = [int(admin_ids_str)]
            
        if not admin_ids:
            raise ValueError
        return admin_ids
        
    except ValueError:
        raise ValueError("Некорректный формат ADMIN_IDS! Укажите числовые ID через запятую или один ID.")

# Основные конфигурационные параметры
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не указан в .env файле!")

# Получаем список админских ID
ADMIN_IDS = get_admin_ids()
print(f"Загруженные админские ID: {ADMIN_IDS}")

# Настройки базы данных
def init_database_path():
    """
    Создаёт директорию для базы данных, если она не существует.
    Возвращает URL для подключения к SQLite.
    """
    db_dir = DB_FILE.parent
    db_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DB_FILE}"

DATABASE_URL = init_database_path()

# Дополнительные параметры (можно добавлять по мере необходимости)
MEDIA_GROUP_TIMEOUT = 5  # Таймаут для сбора медиагруппы в секундах
MAX_PHOTOS_PER_AD = 10   # Максимальное количество фото в одном объявлении