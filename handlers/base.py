import datetime
import logging
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramAPIError

# from utils.functions import send_or_edit
from services.category_service import CategoryService
from services.item_service import ItemService
from services.user_service import UserService

from sqlalchemy.exc import SQLAlchemyError

from handlers.category import show_categories
from handlers.item import show_my_items, start_create_item_from_menu
from handlers.rental import view_my_rentals
from handlers.auth import profile, show_statistics, show_achievements, show_settings

from keyboards.main_kb import get_main_menu_keyboard
from utils.functions import send_reply

# ================= texts =================
# Словарь с соответствиями неправильных команд правильным
COMMAND_SUGGESTIONS = {
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

# Юридическая информация при команде /legal
LEGAL_TEXT = (
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

# Помощь при команде /help
HELP_TEXT = (
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
# ============================================

logger = logging.getLogger(__name__)
base_router = Router()
support_router = Router()

@base_router.message(CommandStart())
@base_router.message(F.text == "🏠 Главное меню")
async def start(message: Message, state: FSMContext, user_service: UserService):
    """Универсальная точка входа.
    - Если пользователя нет — запускает регистрацию.
    - Если есть — приветствует и показывает главное меню"""

    # Если пользователь когда-то застрял в регистрации, aiogram может оставить старое состояние FSM
    # 🧹 очищаем старое состояние FSM, чтобы бот всегда начинал “с чистого листа”
    await state.clear()

    tg_user = message.from_user
    telegram_id = tg_user.id

    try:
        # 1️⃣ Проверяем, есть ли пользователь в БД
        user = await user_service.get_by_telegram_id(telegram_id)

        # 2️⃣ Если новый — регистрируем
        if not user:
            logger.info(f"[/start] Новый пользователь {telegram_id} → переход к регистрации")
            from handlers.auth import start_registration
            return await start_registration(message, user_service)

        # Если нет телефона
        """
        if not user.phone:
            logger.info(f"[/start] Пользователь {telegram_id} не завершил регистрацию → запрос номера")
            from handlers.auth import start_registration
            return await start_registration(message, user_service)
        """

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
        return await show_main_menu(message, user) # , user_service

    except SQLAlchemyError as e:
        logger.error(f"[Start] Ошибка БД при проверке пользователя {telegram_id}: {e}")
        return await message.answer("⚠️ Ошибка базы данных. Попробуйте позже.")
    except TelegramAPIError as e:
        logger.error(f"[Start] Ошибка Telegram API: {e}")
        return await message.answer("⚠️ Ошибка при связи с Telegram. Повторите позже.")
    except Exception as e:
        logger.exception(f"[Start] Неизвестная ошибка {telegram_id}: {e}") # , exc_info=True)
        return await message.answer("⚠️ Непредвиденная ошибка. Попробуйте позже.")


@base_router.callback_query(F.data.in_(["menu:main", "back_to_main_menu"]))
async def show_main_menu_callback(callback: CallbackQuery, user): # user_service: UserService,
    await callback.answer()
    await show_main_menu(callback, user) # , user_service


async def show_main_menu(
    event: Message | CallbackQuery,
    #state: FSMContext,
    #user_service: UserService,
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
    welcome_message = (
        "🏠 <b>Главное меню</b>\n\n "
        f"{greeting}, <b>{user.full_name or 'пользователь'}</b>!\n\n"
        "Выберите действие:"
    )

    # будущие уведомления / активности пользователя / данные поиска
    """
    data = await state.get_data()
    unread_notifications = data.get("unread_notifications", 0)
    if unread_notifications > 0:
        welcome_message += f"\n\n🔔 У вас {unread_notifications} непрочитанных уведомлений"
    
    # Обновляем информацию о последней активности пользователя
    if "user" in context.user_data:
        context.user_data["user"]["last_activity"] = datetime.datetime.now().timestamp()
    
    # Очищаем временные данные поиска
    if "global_search" in context.user_data:
        del context.user_data["global_search"]
    if "for_search" in context.user_data:
        del context.user_data["for_search"]
    """

    # Передаём профиль в клавиатуру
    reply_markup = get_main_menu_keyboard(user)

    # отправка сообщения
    return await send_reply(event, welcome_message, reply_markup=reply_markup)


# ================================== Commands ==================================
@base_router.message(F.text == "/help")
async def help_command(message: Message):
    """Помощь"""
    await message.answer(HELP_TEXT)

@base_router.message(F.text == "/legal")
async def legal_command(message: Message) -> None:
    """Отправляет юридическую информацию при команде /legal."""
    await message.answer(LEGAL_TEXT)

@base_router.message(F.text == "/cancel")
async def cancel(message: Message, state: FSMContext, user): # , user_service: UserService
    """Отмена операции, возврат в главное меню"""
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} отменил текущую операцию")

    """
    # Если это была операция создания объявления, сообщаем пользователю,
    # что его черновик сохранен для будущего использования
    
    # часть-1
    data = await state.get_data()
    draft_item = data.get("draft_item")  # если ты реально используешь этот ключ
    """

    # Очищаем временные данные/ключи - "for_search", "item_data", "search_filters", "search_city" и тп
    await state.clear() # удаляет и состояние, и все данные FSM - все ключи удаляются

    """ 
    # часть-2
    # Если черновик был — возвращаем его обратно в FSM data
    if draft_item is not None:
        await state.update_data(draft_item=draft_item)
        await message.answer(
            "❌ Операция отменена. Черновик объявления сохранён.\n\n"
            "Возвращаемся в главное меню. 🏠"
        )
    else:
        await message.answer("❌ Операция отменена. Возвращаемся в главное меню. 🏠")
    """

    await message.answer("❌ Операция отменена. Возвращаемся в главное меню 🏠")
    return await show_main_menu(message, user) # user_service,


def _get_command_suggestion(command: Optional[str]) -> str: # изменил немного
    if not command:
        return ""

    # Получаем правильную команду или None
    command_lower = command.lower()
    if command_lower in COMMAND_SUGGESTIONS:
        correct_command = COMMAND_SUGGESTIONS[command_lower]
        return f"Используйте команду {correct_command}"

    # Попытка найти похожую команду
    for wrong, correct in COMMAND_SUGGESTIONS.items():
        wrong_text = wrong[1:] if wrong.startswith("/") else wrong
        command_text = command_lower[1:] if command_lower.startswith("/") else command_lower

        if wrong_text in command_text or command_text in wrong_text:
            return f"Возможно, вы имели в виду команду {correct}"

    # Если подсказка не найдена, предлагаем общие команды
    if "профиль" in command_lower or "аккаунт" in command_lower:
        return "Используйте команду /profile для просмотра вашего профиля."
    elif "поиск" in command_lower or "найти" in command_lower or "искать" in command_lower:
        return "Используйте команду /search для поиска вещей в аренду."
    elif "сдать" in command_lower or "аренда" in command_lower or "разместить" in command_lower:
        return "Выберите '📦 Сдать в аренду' в главном меню для размещения объявления."
    elif "сделк" in command_lower or "аренд" in command_lower:
        return "Используйте команду /rentals для просмотра ваших сделок."
    elif "помощь" in command_lower or "справка" in command_lower or "инструкция" in command_lower:
        return "Используйте команду /help для получения справки."
    elif "объявлени" in command_lower or "вещи" in command_lower or "товары" in command_lower:
        return "Используйте команду /items для просмотра ваших объявлений."

    return ""

# Обработка неизвестных команд
@base_router.message(F.text.startswith("/"))
async def unknown_command(message: Message, user): # state: FSMContext, user_service: UserService,
    """Отвечает на неизвестную команду."""
    command = message.text

    suggestions = _get_command_suggestion(command)

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

    await message.answer(reply_text, reply_markup=get_main_menu_keyboard(user))
# =============================================================================================

# ================================== Текстовые сообщения в меню ===============================
@base_router.message(F.text)
async def text_message_handler(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    category_service: CategoryService,
    item_service: ItemService,
    user
):
    """Обрабатывает текстовые сообщения от пользователя в главном меню.

    Определяет команды на основе текста сообщения и вызывает соответствующий обработчик.
    Возвращает состояние разговора для FSM.

    - принимает всё, что не поймал FSM;
    - определяет по тексту (или по ID кнопки), что пользователь хотел;
    - вызывает нужный сценарий (handler-функцию)
    """

    text = message.text.strip() if message.text else ""
    logger.info(f"[MainMenu] Пользователь {user.id} отправил текстовое сообщение в главном меню: '{text}'")

    try:
        # 📞 Поддержка — особая логика (отдельное состояние FSM)
        if text == "📞 Поддержка":
            await ask_support_message(message, state)
            return

        # 🔔 Уведомления — отдельная ветка (не FSM)
        if text.startswith("🔔 Уведомления"):
            #await show_notification_settings(message, state)
            return

        # 🧭 Основная маршрутизация (кнопка -> действие)
        routes = {
            # FSM-сценарии
            # "📞 Поддержка": lambda: start_support_dialog(message, state)
            "🔍 Арендовать": lambda: show_categories(message, category_service),
            "📦 Сдать в аренду": lambda: start_create_item_from_menu(message, state, user_service),
            "📦 Мои объявления": lambda: show_my_items(message, item_service),
            #"📱 Изменить номер": lambda: request_phone_number_change(message, state),

            # Служебные разделы
            "👤 Профиль": lambda: profile(message, user_service),
            "📋 Мои сделки": lambda: view_my_rentals(message, state),
            "⚙️ Настройки": lambda: show_settings(state),
            "📊 Статистика": lambda: show_statistics(state),
            "🏆 Достижения": lambda: show_achievements(state),

            # Системные действия
            "❓ Помощь": lambda: help_command(message),
            "⬅️ Вернуться в меню": lambda: show_main_menu(message, user), # user_service,
        }

        action = routes.get(text)
        if not action: # Если текст не соответствует ни одной кнопке
            logger.warning(f"Неопознанный текст от пользователя {user.id}: '{text}'")
            await message.answer("❓ Неизвестная команда. Используйте меню для навигации.")
            return


    # Безопасный запуск действия - можно так
    #try:
    #    await action()
    except Exception as e:
        logger.exception(f"[MainMenu] Ошибка при выполнении команды {text!r}: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")

# Поддержка - пока сырая
async def ask_support_message(message: Message, state: FSMContext):
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

# пока сырая
@support_router.message(F.text, state="*")
async def process_support_message(message: Message, state: FSMContext, user):
    """Обрабатывает сообщение пользователя для службы поддержки"""
    user_message = message.text

    user_id = user.id
    username = user.username or "нет"
    user_full_name = getattr(user, "full_name", user.first_name)

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
    await message.answer(confirmation_text, parse_mode="HTML")

    # Завершаем сценарий поддержки
    await state.clear()

    # Возвращаем пользователя в главное меню
    return await show_main_menu(message, user)
