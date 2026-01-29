from __future__ import annotations

import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from db.models.support_ticket import SupportTicketStatus
from keyboards.admin_kb import (
    get_admin_support_list_keyboard,
    get_admin_support_ticket_keyboard,
)
from services.admin_service import AdminActionService
from services.support_service import SupportService
from states.support_ticket import SupportStates
from utils.functions import send_or_edit

logger = logging.getLogger(__name__)

admin_support_router = Router()

"""
✅ Definition of Done (проверка за 2 минуты)
        Пользователь пишет /support → бот просит текст → создаётся тикет → “принято”
        Всем админам прилетает сообщение с кнопками “Открыть/Ответить/Закрыть”
        Админ: “Открыть” → видит карточку
        Админ: “Ответить” → пишет → пользователю приходит сообщение
        Админ: “Закрыть” → пользователю приходит уведомление + тикет исчезает из open-списка
        В admin_actions появляются SUPPORT_REPLY и SUPPORT_CLOSE
"""
