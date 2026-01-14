import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Загружаем переменные из .env (локально). Если файла нет — просто пропустит.
load_dotenv()

# ---------------------------- Telegram ----------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError(
        "TELEGRAM_TOKEN is not set. Add it to your environment or to the .env file."
    )


# ---------------------------- Database (SQLite by default) ----------------------------
# Настройки базы данных - используем абсолютный путь для SQLite
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "db")
DB_PATH = os.path.join(DB_DIR, "rental_bot.db")

# создаём директорию, если её нет
os.makedirs(DB_DIR, exist_ok=True)

DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

"""
# Проверяем что файл существует в db директории
if os.path.exists(DB_PATH):
    DATABASE_URL = f"sqlite:///{DB_PATH}"
else:
    # Пробуем путь в корневой директории
    ROOT_DB_PATH = os.path.join(BASE_DIR, 'rental_bot.db')
    if os.path.exists(ROOT_DB_PATH):
        DATABASE_URL = f"sqlite:///{ROOT_DB_PATH}"
    else:
        # Создаем пустую базу данных если ее нет
        DATABASE_URL = f"sqlite:///{DB_PATH}"
"""
8
# ----------------------------------------------------------------------------------
def _parse_admin_ids(raw_value: str | None) -> set[int]:
    """

    :param raw_value: - строка из ENV, например
    :return: set[int] - множество уникальных Telegram ID админов
    """

    if not raw_value: # Сработает, если: raw_value is None, raw_value == "", raw_value == " " не сработает
        logger.warning("ADMIN_IDS is empty — admin access disabled")
        return set() # Возвращает пустое множество

    admin_ids: set[int] = set() # создаёт контейнер для уникальных id
    for part in raw_value.replace(" ", "").split(","):
        # replace(" ", "") - удаляет ТОЛЬКО пробелы " " ("123, 456,789" → replace → "123,456,789")
        # split(",") - разбивает строку по запятым  ("123,456,789" → split → ["123", "456", "789"])
        # !но ("123,,456," → split → ["123", "", "456", ""])
        if not part:
            continue # Пропуск пустых элементов
            # Защищает от: двойных запятых и запятых в конце
            # "123,,456," → пустые строки будут пропущены.
        try:
            admin_ids.add(int(part)) #
            # "123" → 123, "00123" → 123, "foo" → int("foo") вызовет ValueError
        except ValueError:
            logger.warning(f"Invalid admin id in ADMIN_IDS: {part}")
            #continue
    return admin_ids # На выходе множество int, возможно пустое

# значение вычисляется один раз при старте (при импорте)
# middleware/handlers не читают ENV каждый раз
ADMIN_IDS = _parse_admin_ids(os.getenv("ADMIN_IDS"))