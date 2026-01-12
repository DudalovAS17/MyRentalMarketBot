import os
from dotenv import load_dotenv

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