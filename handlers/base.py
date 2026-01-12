import datetime
import logging
import asyncio
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart, Command
from sqlalchemy.exc import SQLAlchemyError
from aiogram.exceptions import TelegramAPIError

# from utils.functions import send_or_edit
from services.category_service import CategoryService
from services.item_service import ItemService
from services.user_service import UserService
"""
from keyboards import (
    get_main_menu_keyboard,
    get_profile_keyboard,
    get_back_keyboard,
    get_extended_back_keyboard,
    get_search_keyboard,
    get_inline_back_keyboard,
)
from states.support import SupportStates  # надо будет завести SupportStates(StatesGroup)
"""

from handlers.category import show_categories
from handlers.item import show_my_items, start_create_item_from_menu
"""
(
    profile,
    show_statistics,
    show_achievements,
    show_settings,
    request_phone_number_change,
    show_notification_settings,
    process_edit_name,
    process_edit_email,
)
"""
#from handlers.rentals import view_my_rentals

from keyboards.main_kb import get_main_menu_keyboard

logger = logging.getLogger(__name__)
base_router = Router()
support_router = Router()

@base_router.message(CommandStart())
#@base_router.message(F.text == "/start") # (F.text.in_({"/start", "/register"}))
@base_router.message(F.text == "🏠 Главное меню")
async def start(message: Message, state: FSMContext, user_service: UserService):
    """Универсальная точка входа.
    - Если пользователя нет — запускает регистрацию.
    - Если есть — приветствует и показывает главное меню"""

    # Если пользователь когда-то застрял в регистрации, aiogram может оставить старое состояние FSM
    await state.clear()  # 🧹 очищаем старое состояние FSM, чтобы бот всегда начинал “с чистого листа”

    tg_user = message.from_user
    telegram_id = tg_user.id

    try:
        # 1️⃣ Проверяем, есть ли пользователь в БД
        user = await user_service.get_by_telegram_id(telegram_id)

        # 2️⃣ Если новый — регистрируем
        if not user:
            logger.info(f"[/start] Новый пользователь {telegram_id} → переход к регистрации")
            from handlers.auth import start_registration
            return await start_registration(message, user_service)  # передаём DI

        # Если нет телефона
        #if not user.phone:
        #    logger.info(f"[/start] Пользователь {telegram_id} не завершил регистрацию → запрос номера")
        #    from handlers.auth import start_registration
        #    return await start_registration(message, user_service)

        # 3️⃣ Пользователь найден, проверяем блокировку
        if user.is_blocked:
            return await message.answer(
                "⚠️ Ваша учётная запись заблокирована. Пожалуйста, обратитесь в службу поддержки."
            )

        # 4️⃣ Если уже зарегистрирован (и имеет номер телефона) - ✅ Приветствие
        await message.answer(
            f"С возвращением, {user.first_name or user.username or 'пользователь'}!\n"
        )

        # 5️⃣ Ведём в главное меню
        return await show_main_menu(message, user_service, user)

    except SQLAlchemyError as e:
        logger.error(f"[Start] Ошибка БД при проверке пользователя {telegram_id}: {e}")
        return await message.answer("⚠️ Ошибка базы данных. Попробуйте позже.")
    except TelegramAPIError as e:
        logger.error(f"[Start] Ошибка Telegram API: {e}")
        return await message.answer("⚠️ Ошибка при связи с Telegram. Повторите позже.")
    except Exception as e:
        logger.exception(f"[Start] Неизвестная ошибка {telegram_id}: {e}") # , exc_info=True)
        return await message.answer("⚠️ Непредвиденная ошибка. Попробуйте позже.")

# Вызов из callback-кнопки
@base_router.callback_query(F.data.in_(["menu:main", "back_to_main_menu"]))
async def show_main_menu_callback(callback: CallbackQuery, user_service: UserService, user):
    await callback.answer()
    await show_main_menu(callback, user_service, user)

async def show_main_menu(
        event: Message | CallbackQuery,
        #state: FSMContext,
        user_service: UserService,
        user
):
    """Показывает главное меню.

    Middleware гарантирует:
      - пользователь существует
      - не заблокирован
      - телефон подтверждён
      - user уже загружен из БД и передан сюда
    """

    now = datetime.datetime.now().hour
    greeting = (
        "Доброе утро" if 5 <= now < 12 else
        "Добрый день" if 12 <= now < 18 else
        "Добрый вечер"
    )

    welcome_message = ("🏠 <b>Главное меню</b>\n\n "
                       f"{greeting}, <b>{user.full_name or 'пользователь'}</b>!\n\n"
                       "Выберите действие:")

    # реализую, когда будет сервис уведомлений
    #data = await state.get_data()
    #unread_notifications = data.get("unread_notifications", 0)
    #if unread_notifications > 0:
    #    welcome_message += f"\n\n🔔 У вас {unread_notifications} непрочитанных уведомлений"

    """Еще предстоит реализовать
    # Обновляем информацию о последней активности пользователя
    if "user" in context.user_data:
        context.user_data["user"]["last_activity"] = datetime.datetime.now().timestamp()
    
    # Очищаем временные данные поиска
    if "global_search" in context.user_data:
        del context.user_data["global_search"]
    if "for_search" in context.user_data:
        del context.user_data["for_search"]"""

    # Передаём профиль в клавиатуру
    reply_markup = get_main_menu_keyboard(user)

    # "Возвращаемся в главное меню..."
    # 1️⃣ Если это CallbackQuery → не редактируем!
    # ReplyKeyboardMarkup НЕЛЬЗЯ вставить в edit_message_text
    if isinstance(event, CallbackQuery):
        return await event.message.answer(welcome_message, reply_markup=reply_markup, parse_mode="HTML")

    # 2️⃣ Если это обычное Message
    return await event.answer(welcome_message, reply_markup=reply_markup, parse_mode="HTML")


@base_router.message(F.text == "/help")
async def help_command(message: Message):
    """Помощь"""
    help_text = (
        "🔍 <b>Как пользоваться ботом</b>\n\n"
        "<b>Основные команды:</b>\n"
        "✅ /start - Запуск бота и показ главного меню\n"
        "🔍 /search - Поиск вещей для аренды\n"
        "📦 /items - Управление моими объявлениями\n"
        "🤝 /rentals - Просмотр моих сделок\n"
        "👤 /profile - Просмотр личного профиля\n"
        "📜 /legal - Юридическая информация\n"
        "❓ /help - Вывод этой справки\n"
        "❌ /cancel - Отмена текущей операции\n\n"

        "<b>Как арендовать вещь:</b>\n"
        "1️⃣ Нажмите '🔍 Арендовать' в главном меню или используйте команду /search\n"
        "2️⃣ Выберите категорию или воспользуйтесь поиском по городу\n"
        "3️⃣ Просмотрите доступные объявления\n"
        "4️⃣ Выберите подходящее объявление\n"
        "5️⃣ Нажмите кнопку 'Арендовать' и следуйте инструкциям\n\n"

        "<b>Как сдать вещь в аренду:</b>\n"
        "1️⃣ Нажмите '📦 Сдать в аренду' в главном меню\n"
        "2️⃣ Введите информацию о вещи (название, описание, фото)\n"
        "3️⃣ Укажите стоимость аренды и сумму залога\n"
        "4️⃣ Укажите ваше местоположение 📍\n"
        "5️⃣ Опубликуйте объявление 🚀\n\n"

        "<b>Управление сделками:</b>\n"
        "В разделе '📋 Мои сделки' вы можете:\n"
        "- 📋 Просматривать активные и завершенные сделки\n"
        "- ✅ Подтверждать передачу и возврат вещей\n"
        "- ⭐ Оставлять отзывы после завершения аренды\n\n"

        "📱 По всем вопросам обращайтесь в раздел '📞 Поддержка'"
    )
    await message.answer(help_text)


@base_router.message(F.text == "/legal")
async def legal_command(message: Message) -> None:
    """Отправляет юридическую информацию при команде /legal."""
    legal_text = (
        "📝 <b>Юридическая информация</b>\n\n"
        "Пользуясь ботом 'Аренда.рф', вы соглашаетесь с нашими условиями пользования и политикой конфиденциальности.\n\n"

        "📃 <b>Публичная оферта:</b>\n"
        "Содержит основные правила платформы, условия аренды, права и обязанности сторон.\n\n"

        "✍️ <b>Пользовательское соглашение:</b>\n"
        "Описывает условия использования бота и ответственность сторон.\n\n"

        "🔒 <b>Политика конфиденциальности:</b>\n"
        "Регулирует сбор, хранение и использование ваших персональных данных в соответствии с ФЗ-152.\n\n"

        "📄 <b>Договор аренды:</b>\n"
        "Формируется автоматически при заключении сделки и содержит все необходимые условия аренды.\n\n"

        "💼 Полные тексты документов будут предоставлены по запросу."
    )
    await message.answer(legal_text)


@base_router.message(F.text == "/cancel")
async def cancel(message: Message, state: FSMContext, user_service: UserService):
    """Отмена операции, возврат в главное меню"""
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} отменил текущую операцию")

    """ нужно будет реализовать
    # Очищаем временные данные операции
    keys_to_clear = [
        "selected_category_id", "selected_category_name", 
        "global_search", "for_search", "item_data", 
        "search_filters", "search_city", "temp_item"
    ]
    
    for key in keys_to_clear:
        if key in context.user_data:
            del context.user_data[key]
    
    # Если это была операция создания объявления, сообщаем пользователю,
    # что его черновик сохранен для будущего использования
    if "draft_item" in context.user_data:
        await update.message.reply_text(
            "❌ Операция отменена. Ваш черновик объявления сохранен и будет доступен "
            "при следующей попытке создания объявления.\n\n"
            "Возвращаемся в главное меню. 🏠"
        )
    else:
        await update.message.reply_text(
            "❌ Операция отменена. Возвращаемся в главное меню. 🏠"
        )
    """
    await state.clear()
    await message.answer("❌ Операция отменена. Возвращаемся в главное меню 🏠")
    return await show_main_menu(message, user_service)


# ================= Обработка неизвестных команд =================

@base_router.message(F.text.startswith("/"))
async def unknown_command(message: Message, state: FSMContext, user_service: UserService):
    """Отвечает на неизвестную команду."""
    command = message.text

    # Предложения по корректным командам на основе неизвестной команды
    suggestions = ""

    # Словарь с соответствиями неправильных команд правильным
    command_suggestions = {
        # Команды для сделок
        "/мои сделки": "/rentals",
        "/сделки": "/rentals",
        "/аренды": "/rentals",
        "/rentals": "/rentals",
        "/rental": "/rentals",

        # Команды для поиска
        "/найти": "/search",
        "/поиск": "/search",
        "/искать": "/search",
        "/find": "/search",

        # Команды для профиля
        "/профиль": "/profile",
        "/личный кабинет": "/profile",
        "/аккаунт": "/profile",
        "/account": "/profile",

        # Команды для помощи
        "/помощь": "/help",
        "/справка": "/help",
        "/инфо": "/help",
        "/инструкция": "/help",

        # Команды для объявлений
        "/объявления": "/items",
        "/мои объявления": "/items",
        "/мои вещи": "/items",
        "/мои товары": "/items",
        "/items": "/items",

        # Команды для старта
        "/старт": "/start",
        "/начать": "/start",
        "/перезапуск": "/start"
    }

    # Получаем правильную команду или None
    command_lower = command.lower()
    if command_lower in command_suggestions:
        correct_command = command_suggestions[command_lower]
        suggestions = f"Используйте команду {correct_command}"
    else:
        # Попытка найти похожую команду
        for wrong, correct in command_suggestions.items():
            wrong_text = wrong[1:] if wrong.startswith("/") else wrong
            command_text = command_lower[1:] if command_lower.startswith("/") else command_lower

            if wrong_text in command_text or command_text in wrong_text:
                suggestions = f"Возможно, вы имели в виду команду {correct}"
                break

        # Если подсказка не найдена, предлагаем общие команды
        if not suggestions:
            if "профиль" in command_lower or "аккаунт" in command_lower:
                suggestions = "Используйте команду /profile для просмотра вашего профиля."
            elif "поиск" in command_lower or "найти" in command_lower or "искать" in command_lower:
                suggestions = "Используйте команду /search для поиска вещей в аренду."
            elif "сдать" in command_lower or "аренда" in command_lower or "разместить" in command_lower:
                suggestions = "Выберите '📦 Сдать в аренду' в главном меню для размещения объявления."
            elif "сделк" in command_lower or "аренд" in command_lower:
                suggestions = "Используйте команду /rentals для просмотра ваших сделок."
            elif "помощь" in command_lower or "справка" in command_lower or "инструкция" in command_lower:
                suggestions = "Используйте команду /help для получения справки."
            elif "объявлени" in command_lower or "вещи" in command_lower or "товары" in command_lower:
                suggestions = "Используйте команду /items для просмотра ваших объявлений."

    # Формируем сообщение с подсказкой
    reply_text = (
        "⚠️ Извините, я не понимаю эту команду. Пожалуйста, используйте /help для просмотра доступных команд."
    )

    if suggestions:
        reply_text += f"\n\n💡 {suggestions}"

    reply_text += "\n\n🔹 Основные команды:\n"
    reply_text += "/start - Главное меню\n"
    reply_text += "/search - Поиск вещей\n"
    reply_text += "/rentals - Мои сделки\n"
    reply_text += "/items - Мои объявления\n"
    reply_text += "/profile - Профиль\n"
    reply_text += "/help - Справка"

    user = await user_service.get_by_telegram_id(message.from_user.id)

    await message.answer(
        reply_text,
        reply_markup=get_main_menu_keyboard(user) # ?
    )

# ================= Текстовые сообщения в меню =================
@base_router.message(F.text)
async def text_message_handler(
        message: Message,
        state: FSMContext,
        user_service: UserService,
        category_service: CategoryService,
        item_service: ItemService,
):
    """Обрабатывает текстовые сообщения от пользователя в главном меню.

    Определяет команды на основе текста сообщения и вызывает соответствующий обработчик.
    Возвращает состояние разговора для FSM.

    - принимает всё, что не поймал FSM;
    - определяет по тексту (или по ID кнопки), что пользователь хотел;
    - вызывает нужный сценарий (handler-функцию)
    """

    text = message.text.strip() if message.text else ""
    user = message.from_user
    logger.info(f"[MainMenu] Пользователь {user.id} отправил текстовое сообщение в главном меню: '{text}'")

    # Проверяем, не заблокирован ли пользователь
    db_user = await user_service.get_by_telegram_id(user.id)
    if db_user and db_user.is_blocked: # getattr(db_user, "is_blocked", False)
        logger.warning(f"[MainMenu] Заблокированный пользователь {user.id} пытается взаимодействовать с ботом")
        await message.answer("⚠️ Ваш аккаунт заблокирован. Пожалуйста, обратитесь в поддержку.")
        return

    try:
        # 📞 Поддержка — особая логика (отдельное состояние FSM)
        if text == "📞 Поддержка":
            await ask_support_message(message, state)
            return

        # 🔔 Уведомления — отдельная ветка (не FSM)
        if text.startswith("🔔 Уведомления"):
            await show_notification_settings(message, state)
            return

        """Интересный момент
        FSM-aware dispatcher — можно в будущем добавить фильтр:
        если FSM активно, не обрабатывать текстовые команды."""

        # 🧭 Основная маршрутизация через match-case
        match text:

            # FSM-сценарии
            #case "📞 Поддержка":
            #    await start_support_dialog(message, state)
            case "🔍 Арендовать":
                await show_categories(message, category_service) # state, for_search=True
            case "📦 Сдать в аренду":
                await start_create_item_from_menu(message, state, user_service)
            case "📦 Мои объявления":
                await show_my_items(message, item_service) # , state
            case "📱 Изменить номер":
                await request_phone_number_change(message, state)

            # Служебные разделы
            #case "👤 Профиль":
            #    from handlers.auth import profile
            #    await profile(message, user_service)
            case "📋 Мои сделки":
                await view_my_rentals(message, state)
            case "⚙️ Настройки":
                await show_settings(message, state)
            case "📊 Статистика":
                await show_statistics(message, state)
            case "🏆 Достижения":
                await show_achievements(message, state)

            # Системные действия
            case "❓ Помощь":
                await help_command(message)
            case "⬅️ Вернуться в меню":
                await show_main_menu(message, user_service)

            case _:
                # Если текст не соответствует ни одной кнопке
                logger.warning(f"Неопознанный текст от пользователя {user.id}: '{text}'")
                await message.answer("❓ Неизвестная команда. Используйте меню для навигации.")

    except Exception as e:
        logger.exception(f"[MainMenu] Ошибка при выполнении команды {text!r}: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")


# ================= Поддержка =================

# тут пока сырая
async def ask_support_message(
        message: Message,
        state: FSMContext,
):
    support_request_text = (
        "📞 <b>Поддержка</b>\n\n"
        "Пожалуйста, опишите вашу проблему или вопрос как можно подробнее. "
        "Наши специалисты постараются вам помочь."
    )
    keyboard = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_support")]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(
        support_request_text,
        reply_markup=reply_markup
    )
    # Устанавливаем состояние FSM для поддержки
    await state.set_state(SupportStates.waiting_message)

"""
@support_router.message(F.text, state="*")
async def process_support_message(message: Message, state: FSMContext, user_service: UserService):
    ""Обрабатывает сообщение пользователя для службы поддержки""
    user_message = message.text
    user = message.from_user
    user_id = user.id
    username = user.username or "нет"

    # Получаем данные пользователя из БД
    db_user = user_service.get_by_telegram_id(user_id)
    user_full_name = getattr(db_user, "full_name", user.first_name)

    # Логируем сообщение
    logger.info(
        f"Получено сообщение в поддержку от {user_full_name} ({user_id} @{username}): '{user_message}'"
    )

    # Формируем сообщение для "отправки" в поддержку (можно отправлять админам)
    support_message_to_admin = (
        f"🆘 <b>Новое обращение в поддержку</b> 🆘\n\n"
        f"<b>От:</b> {user_full_name} (ID: <code>{user_id}</code>, @{username})\n"
        f"<b>Сообщение:</b>\n"
        f"{user_message}"
    )

    # TODO: Реализовать отправку этого сообщения администраторам
    # from config import ADMIN_USER_IDS
    # for admin_id in ADMIN_USER_IDS:
    #     try:
    #         await message.bot.send_message(
    #             chat_id=admin_id,
    #             text=support_message_to_admin,
    #             parse_mode="HTML"
    #         )
    #     except Exception as e:
    #         logger.error(f"Не удалось отправить сообщение поддержки админу {admin_id}: {e}")

    # Отправляем подтверждение пользователю
    confirmation_text = (
        "✅ <b>Спасибо за ваше обращение!</b>\n\n"
        "Ваше сообщение получено и будет рассмотрено нашей службой поддержки в ближайшее время.\n\n"
        "Мы свяжемся с вами, если потребуется дополнительная информация."
    )
    await message.answer(confirmation_text)

    # Возвращаем пользователя в главное меню
    return await show_main_menu(message, state, user_service)
"""