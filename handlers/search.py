import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from services.item_service import ItemService
from states.search import SearchStates
from utils.functions import format_price, send_or_edit

logger = logging.getLogger(__name__)

search_router = Router()  # <-- подключим в main.py
