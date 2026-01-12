# app/handlers/base.py
import asyncio
import datetime
import importlib
import logging
from typing import Optional, Union, Callable, Awaitable

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)

from app.config import settings

logger = logging.getLogger(__name__)
router = Router(name="base")


# ──────────────────────────────
# FSM
# ──────────────────────────────
class BaseStates(StatesGroup):
    main = State()


class SupportStates(StatesGroup):
    waiting_message = State()


# ──────────────────────────────
# Helpers
# ──────────────────────────────
async def run_db(func: Callable, *args, **kwargs):
    """Безопасно вызываем синхронные сервисы/репозитории из async-кода."""
    return await asyncio.to_thread(func, *args, **kwargs)


def _fallback_main_menu_keyboard(_: dict | None = None) -> ReplyKeyboardMarkup:
    """
    Запасной вариант главного меню, если свой модуль keyboards ещё не перенесён.
    Замените на импорт из app.keyboards, когда будет готово.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Арендовать"), KeyboardButton(text="📦 Сдать в аренду")],
            [KeyboardButton(text="📋 Мои сделки"), KeyboardButton(text="📦 Мои объявления")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="❓ Помощь")],
            [KeyboardButton(text="📞 Поддержка")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие…",
    )


def get_main_menu_keyboard_safe(user_data: dict | None = None) -> ReplyKeyboardMarkup:
    """
    Пробуем взять вашу реализацию из app.keyboards.get_main_menu_keyboard,
    иначе используем фолбэк.
    """
    try:
        from app.keyboards import get_main_menu_keyboard  # ваш aiogram-вариант
        return get_main_menu_keyboard(user_data or {})
    except Exception:
        return _fallback_main_menu_keyboard(user_data or {})


async def _safe_edit_message(
    event: Union[Message, CallbackQuery],
    text: Optional[str] = None,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
):
    """
    Пытаемся отредактировать сообщение (если это callback). Если не вышло — шлём новое.
    """
    if isinstance(event, CallbackQuery):
        try:
            await event.answer()
        except Exception:
            pass
        try:
            if text is not None:
                await event.message.edit_text(text=text, reply_markup=reply_markup)
                return
        except Exception as e:
            logger.debug(f"edit_text failed: {e}")
        # отправляем новое
        if text is not None:
            await event.message.answer(text=text, reply_markup=reply_markup)
    else:
        # Message
        if text is not None:
            await event.answer(text, reply_markup=reply_markup)


def _greeting_by_time(dt: Optional[datetime.datetime] = None) -> str:
    h = (dt or datetime.datetime.now()).hour
    if 5 <= h < 12:
        return "Доброе утро"
    if 12 <= h < 18:
        return "Добрый день"
    return "Добрый вечер"


async def _call_transitional_handler_or_stub(
    message: Message,
    state: FSMContext,
    dotted_path: str,
    func_name: str,
    *,
    stub_text: str,
):
    """
    Аккуратно вызываем обработчик из ещё-неперенесённых модулей.
    Как только модуль будет перенесён в app.handlers.*, просто замените dotted_path/func_name.
    """
    try:
        mod = importlib.import_module(dotted_path)
        func = getattr(mod, func_name, None)
        if func is None:
            raise AttributeError(f"{func_name} not found in {dotted_path}")
        result = func(message, state)  # предполагаем сигнатуру (Message, FSMContext)
        if asyncio.iscoroutine(result):
            await result
        return
    except Exception as e:
        logger.warning(f"Раздел не перенесён или вызов упал ({dotted_path}.{func_name}): {e}")
        await message.answer(stub_text)


# ──────────────────────────────
# Главная: /start, /menu, «назад»
# ──────────────────────────────
async def show_main_menu(event: Union[Message, CallbackQuery], state: FSMContext):
    """
    Отрисовывает главное меню. Можно вызывать и из Message, и из CallbackQuery.
    """
    # Достаём user (если вы сохраняете его в FSM), иначе тянем из БД по telegram_id
    data = await state.get_data()
    user_cached = (data or {}).get("user", {})

    tg_id = event.from_user.id if isinstance(event, CallbackQuery) else event.from_user.id

    user = None
    try:
        # Импортируем тут, чтобы не ломаться, если services ещё не в sys.path
        from services.auth_service import AuthService  # ваш синхронный сервис
        user = await run_db(AuthService.get_user_by_telegram_id, tg_id)
    except Exception as e:
        logger.warning(f"AuthService недоступен (или БД): {e}")

    if not user:
        text = (
            "❌ Ваш профиль не найден. Пожалуйста, пройдите регистрацию через /start.\n\n"
            "Если вы уже регистрировались, попробуйте ещё раз или напишите в 📞 Поддержка."
        )
        await _safe_edit_message(event, text=text, reply_markup=None)
        # Состояние главного меню всё равно зададим, чтобы ловить кнопки
        await state.set_state(BaseStates.main)
        return

    greeting = _greeting_by_time()
    welcome = ["🏠 <b>Главное меню</b>\n"]
    if getattr(user, "full_name", None):
        welcome.append(f"{greeting}, <b>{user.full_name}</b>!\n")
    welcome.append("Выберите действие:")
    text = "\n".join(welcome)

    # Непрочитанные уведомления (если вы храните это в FSM-data)
    unread_notifications = (user_cached or {}).get("unread_notifications", 0)
    if unread_notifications > 0:
        text += f"\n\n🔔 У вас {unread_notifications} непрочитанных уведомлений."

    kb = get_main_menu_keyboard_safe(user_cached)

    # Ставим отметку об активности
    await state.update_data(user={**user_cached, "last_activity": datetime.datetime.now().timestamp()})

    # Рисуем
    await _safe_edit_message(event, text=text, reply_markup=None)
    # Для обычного меню используем reply-клавиатуру отдельным сообщением (если нужно)
    if isinstance(event, CallbackQuery):
        await event.message.answer("⬇️ Доступные действия:", reply_markup=kb)
    else:
        # Если это обычное /start — уже ответили выше? Дублировать не будем.
        await event.answer(text, reply_markup=kb)

    await state.set_state(BaseStates.main)


@router.message(CommandStart())
async def on_start(message: Message, state: FSMContext):
    # очищаем предыдущее состояние и открываем меню
    await state.clear()
    await show_main_menu(message, state)


@router.message(Command("menu"))
async def on_menu(message: Message, state: FSMContext):
    await show_main_menu(message, state)


@router.callback_query(F.data == "back_to_menu")
async def on_back_to_menu(call: CallbackQuery, state: FSMContext):
    await show_main_menu(call, state)


# ──────────────────────────────
# /help, /legal
# ──────────────────────────────
@router.message(Command("help"))
async def help_command(message: Message):
    help_text = (
        "🔍 <b>Как пользоваться ботом</b>\n\n"
        "<b>Основные команды:</b>\n"
        "✅ /start — Запуск бота и главное меню\n"
        "🔍 /search — Поиск вещей для аренды\n"
        "📦 /items — Управление моими объявлениями\n"
        "🤝 /rentals — Просмотр моих сделок\n"
        "👤 /profile — Просмотр личного профиля\n"
        "📜 /legal — Юридическая информация\n"
        "❓ /help — Эта справка\n"
        "❌ /cancel — Отмена текущей операции\n\n"
        "<b>Как арендовать:</b>\n"
        "1) «🔍 Арендовать» в меню или /search\n"
        "2) Выбор категории/поиск по городу\n"
        "3) Просмотр объявлений → «Арендовать» и следовать инструкциям\n\n"
        "<b>Как сдать вещь:</b>\n"
        "1) «📦 Сдать в аренду»\n"
        "2) Название, описание, фото\n"
        "3) Цена и залог\n"
        "4) Локация\n"
        "5) Публикация 🚀\n\n"
        "📱 По вопросам — раздел «📞 Поддержка»."
    )
    await message.answer(help_text)


@router.message(Command("legal"))
async def legal_command(message: Message):
    legal_text = (
        "📝 <b>Юридическая информация</b>\n\n"
        "Пользуясь платформой, вы соглашаетесь с условиями и политикой конфиденциальности.\n\n"
        "📃 <b>Публичная оферта</b> — правила платформы, аренда, права и обязанности.\n"
        "✍️ <b>Пользовательское соглашение</b> — условия использования и ответственность.\n"
        "🔒 <b>Политика конфиденциальности</b> — обработка персональных данных.\n"
        "📄 <b>Договор аренды</b> — формируется при заключении сделки.\n\n"
        "Полные тексты документов предоставим по запросу."
    )
    await message.answer(legal_text)


# ──────────────────────────────
# /cancel + кнопка отмены поддержки
# ──────────────────────────────
@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} отменил текущую операцию")

    data = await state.get_data()
    # Можно подчистить только временные ключи, но чаще проще сбросить всё:
    await state.clear()

    if "draft_item" in (data or {}):
        await message.answer(
            "❌ Операция отменена. Черновик сохранён и будет доступен при следующей попытке.\n\n"
            "Возвращаемся в главное меню. 🏠",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await message.answer("❌ Операция отменена. Возвращаемся в главное меню. 🏠", reply_markup=ReplyKeyboardRemove())

    await show_main_menu(message, state)


@router.callback_query(F.data == "cancel_support")
async def cancel_support(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer("Отменено.")
    await show_main_menu(call, state)


# ──────────────────────────────
# Поддержка (кнопка в меню → ввод → отправка админам)
# ──────────────────────────────
@router.message(BaseStates.main, F.text == "📞 Поддержка")
async def support_entry(message: Message, state: FSMContext):
    text = (
        "📞 <b>Поддержка</b>\n\n"
        "Опишите вашу проблему одним сообщением. Мы передадим его администраторам."
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_support")]]
    )
    await message.answer(text, reply_markup=kb)
    await state.set_state(SupportStates.waiting_message)


@router.message(SupportStates.waiting_message, F.text)
async def process_support_message(message: Message, state: FSMContext):
    user = message.from_user
    user_full_name = user.full_name
    user_id = user.id
    username = f"@{user.username}" if user.username else "нет"
    user_message = message.text

    logger.info(f"Получено сообщение в поддержку от {user_full_name} ({user_id} {username}): '{user_message}'")

    to_admin = (
        "🆘 <b>Новое обращение в поддержку</b>\n\n"
        f"<b>От:</b> {user_full_name} (ID: <code>{user_id}</code>, {username})\n"
        f"<b>Сообщение:</b>\n{user_message}"
    )

    # Отправка админам
    for admin_id in settings.ADMINS:
        try:
            await message.bot.send_message(chat_id=admin_id, text=to_admin)
        except Exception as e:
            logger.error(f"Не удалось отправить админу {admin_id}: {e}")

    await message.answer(
        "✅ <b>Спасибо! Ваше обращение получено.</b>\nМы свяжемся с вами при необходимости.",
        reply_markup=ReplyKeyboardRemove(),
    )

    # Возврат в главное меню
    await state.clear()
    await show_main_menu(message, state)


# ──────────────────────────────
# Кнопки главного меню (текстовые)
# Пока заглушки — замените на реальные вызовы после переноса соответствующих модулей
# ──────────────────────────────
@router.message(BaseStates.main, F.text == "⬅️ Вернуться в меню")
async def back_to_menu_button(message: Message, state: FSMContext):
    await show_main_menu(message, state)


@router.message(BaseStates.main, F.text == "❓ Помощь")
async def help_button(message: Message, state: FSMContext):
    await help_command(message)


@router.message(BaseStates.main, F.text == "🔍 Арендовать")
async def rent_search_button(message: Message, state: FSMContext):
    # Замените на перенос: app.handlers.category.show_categories(message, state, for_search=True)
    await _call_transitional_handler_or_stub(
        message, state,
        dotted_path="app.handlers.category",
        func_name="show_categories",
        stub_text="Раздел «Категории/Поиск» ещё не перенесён на aiogram.",
    )


@router.message(BaseStates.main, F.text == "📦 Сдать в аренду")
async def rent_offer_button(message: Message, state: FSMContext):
    # Замените на перенос: app.handlers.category.show_categories(message, state, for_search=False)
    await _call_transitional_handler_or_stub(
        message, state,
        dotted_path="app.handlers.category",
        func_name="show_categories",
        stub_text="Раздел «Категории/Создание объявления» ещё не перенесён на aiogram.",
    )


@router.message(BaseStates.main, F.text == "📋 Мои сделки")
async def my_rentals_button(message: Message, state: FSMContext):
    await _call_transitional_handler_or_stub(
        message, state,
        dotted_path="app.handlers.rentals",
        func_name="view_my_rentals",
        stub_text="Раздел «Мои сделки» ещё не перенесён на aiogram.",
    )


@router.message(BaseStates.main, F.text == "📦 Мои объявления")
async def my_items_button(message: Message, state: FSMContext):
    await _call_transitional_handler_or_stub(
        message, state,
        dotted_path="app.handlers.items",
        func_name="show_my_items",
        stub_text="Раздел «Мои объявления» ещё не перенесён на aiogram.",
    )


@router.message(BaseStates.main, F.text == "👤 Профиль")
async def profile_button(message: Message, state: FSMContext):
    await _call_transitional_handler_or_stub(
        message, state,
        dotted_path="app.handlers.auth",
        func_name="profile",
        stub_text="Раздел «Профиль» ещё не перенесён на aiogram.",
    )


@router.message(BaseStates.main, F.text.startswith("🔔 Уведомления"))
async def notifications_button(message: Message, state: FSMContext):
    await _call_transitional_handler_or_stub(
        message, state,
        dotted_path="app.handlers.auth",
        func_name="show_notification_settings",
        stub_text="Раздел «Уведомления» ещё не перенесён на aiogram.",
    )


# ──────────────────────────────
# Неизвестная команда (последним)
# ──────────────────────────────
@router.message(F.text.startswith("/"))
async def unknown_command(message: Message, state: FSMContext):
    command = message.text or ""
    command_lower = command.lower()

    command_suggestions = {
        # сделки
        "/мои сделки": "/rentals",
        "/сделки": "/rentals",
        "/аренды": "/rentals",
        "/rental": "/rentals",
        # поиск
        "/найти": "/search",
        "/поиск": "/search",
        "/искать": "/search",
        "/find": "/search",
        # профиль
        "/профиль": "/profile",
        "/личный кабинет": "/profile",
        "/аккаунт": "/profile",
        "/account": "/profile",
        # помощь
        "/помощь": "/help",
        "/справка": "/help",
        "/инфо": "/help",
        "/инструкция": "/help",
        # объявления
        "/объявления": "/items",
        "/мои объявления": "/items",
        "/мои вещи": "/items",
        "/мои товары": "/items",
        # старт
        "/старт": "/start",
        "/начать": "/start",
        "/перезапуск": "/start",
    }

    suggestions = ""
    if command_lower in command_suggestions:
        suggestions = f"Используйте команду {command_suggestions[command_lower]}"
    else:
        for wrong, correct in command_suggestions.items():
            wt = wrong[1:] if wrong.startswith("/") else wrong
            ct = command_lower[1:] if command_lower.startswith("/") else command_lower
            if wt in ct or ct in wt:
                suggestions = f"Возможно, вы имели в виду {correct}"
                break

    msg = (
        "⚠️ Я не понимаю эту команду. Посмотрите /help для доступных команд."
    )
    if suggestions:
        msg += f"\n\n💡 {suggestions}"

    msg += (
        "\n\n🔹 Основные команды:\n"
        "/start — главное меню\n"
        "/search — поиск вещей\n"
        "/rentals — мои сделки\n"
        "/items — мои объявления\n"
        "/profile — профиль\n"
        "/help — справка"
    )

    await message.answer(msg, reply_markup=get_main_menu_keyboard_safe((await state.get_data()).get("user", {})))
