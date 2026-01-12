import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

# Импортируем свои константы (пути назад и т.п.)
#from keyboards.constants import BACK_CB

logger = logging.getLogger(__name__)

search_router = Router()  # <-- подключим в main.py

@search_router.callback_query(F.data == "search_all")
async def search_in_all_categories(callback: CallbackQuery, state: FSMContext):
    """Поиск по всем категориям.
    Показываем популярные объявления из разных категорий"""
