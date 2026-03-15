import logging
import re
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from services.user_service import UserService
from handlers.base import show_main_menu
from schemas.user import UserCreate, UserUpdate
from utils.functions import send_or_edit
from states.user import ProfileEditStates
from keyboards.user_kb import profile_settings_back_keyboard, get_profile_keyboard

logger = logging.getLogger(__name__)
auth_router = Router() # Router(name="auth")


async def start_registration(
    message: Message,
    user_service: UserService,
):
    """Только сценарий НОВОГО пользователя:
    - создаём запись (или upsert, если хочешь)
    - просим контакт (телефон)
    Никаких проверок блокировки/«уже зарегистрирован» — это задача /start.
    """
    tg_user = message.from_user
    telegram_id = tg_user.id

    user_data = UserCreate(
        telegram_id=telegram_id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
        full_name=f"{tg_user.first_name or ''} {tg_user.last_name or ''}".strip(),
        phone=None,
        email=None
    )

    try:
        # Регистрируем пользователя или получаем существующего
        await user_service.create(user_data)
        logger.info(f"Создан новый пользователь с Telegram ID {telegram_id}")

    except IntegrityError:
        # такой пользователь уже есть (дубликат telegram_id)
        logger.warning("Попытка повторной регистрации пользователя %s", telegram_id)
        await message.answer("⚠️ Вы уже зарегистрированы. Используйте /start для входа в меню.")
        return

    except SQLAlchemyError as e:
        logger.error("Ошибка БД при регистрации %s: %s", telegram_id, e)
        await message.answer(
            "❌ Произошла ошибка при подключении к базе данных. Попробуйте позже."
        )
        return

    except Exception as e:
        logger.exception("Неожиданная ошибка при регистрации %s", telegram_id)
        # logger.error(f"Ошибка при регистрации пользователя {telegram_id}: {e}", exc_info=True)
        await message.answer("⚠️ Произошла внутренняя ошибка. Попробуйте позже.")
        # f"⚠️ {tg_user.first_name or 'Пользователь'},
        return

    # # запрашиваем телефон пользователя
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await message.answer(
        "👋 Приветствуем в <b>Аренда.рф</b>!\n\n"
        "Здесь вы можете сдавать и арендовать вещи по всей России.\n\n"
        "Для безопасности, пожалуйста, подтвердите номер телефона:",
        # тут надо норм текст при для 1й регистрации
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    # FSM перейдёт в состояние PHONE_NUMBER позже (в обработчике контакта)

@auth_router.message(F.contact)
async def process_phone_number(
    message: Message,
    state: FSMContext,
    user_service: UserService,
):
    """
    Обрабатывает контакт-телефон:
    ✔ Регистрация нового пользователя
    ✔ Смена номера через settings ("change_phone")

    При любом исходе FSM-регистрации закроется в этой функции"""

    contact = message.contact
    tg_user = message.from_user
    # tg_user — это Telegram-пользователь (Это всё данные из Telegram, не из БД)
    # Но этот пользователь НЕ хранится в твоей базе
    # user — это SQLAlchemy-модель из middleware (Это твоя база данных)

    # Проверка корректности контакта
    if not contact or contact.user_id != tg_user.id:
        logger.info(f"[Регистрация] Номер телефона не получен или принадлежит другому пользователю ({tg_user.id})")
        text = (
            "⚠️ Пожалуйста, используйте кнопку ниже, чтобы отправить свой **реальный контакт**.\n\n"
            "Это нужно для подтверждения вашего номера телефона."
        )

        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await message.answer(text, reply_markup=keyboard)
        return  # FSM остаётся в том же состоянии (ожидает контакт)

    phone_number = contact.phone_number
    logger.debug(f"[Регистрация] Получен номер телефона {phone_number} от пользователя {tg_user.id}")

    # Проверяем: это регистрация или смена номера
    data = await state.get_data()
    is_changing_phone = data.get("changing_phone", False)

    db_user = await user_service.get_by_telegram_id(tg_user.id)
    if not db_user:
        logger.info(f"[Auth] Пользователь {tg_user.id} не найден → предложить регистрацию")
        await  message.answer("❌ Ваш профиль не найден. Пожалуйста, зарегистрируйтесь через /start")
        return

    try:
        # Обновляем телефон
        updated = await user_service.update(db_user.id,  UserUpdate(phone=phone_number))
        if not updated:
            logger.error(f"Не удалось обновить номер телефона для пользователя {tg_user.id}")
            await message.answer("❌ Ошибка при сохранении номера. Попробуйте позже.")
            return

        # Если аккаунт заблокирован
        if updated.is_blocked:
            await message.answer("🚫 Ваш аккаунт заблокирован. Обратитесь в поддержку.")
            return

        # Сценарий 2: смена номера телефона (убрал отсюда)
        if is_changing_phone:
            await state.update_data(changing_phone=False)   # снимаем флаг
            await message.answer(
                f"✅ Ваш новый номер сохранён: <b>{phone_number}</b>",
                parse_mode="HTML"
            )

            # возвращаем в профиль
            await message.answer("🔙 Возвращаем вас в профиль...",
                                 reply_markup=InlineKeyboardMarkup(
                                     inline_keyboard=[
                                         [InlineKeyboardButton(text="Открыть профиль", callback_data="back_to_profile")]
                                     ]
                                 ))
            return

        # Сценарий 1: регистрация
        await message.answer(
            "✅ Спасибо! Номер телефона подтверждён.\n\n"
            "Теперь вы можете использовать все функции платформы <b>Аренда.рф</b>.",
            parse_mode="HTML"
        )

        await state.clear() # ??? чтобы FSM после регистрации гарантированно завершался
        await show_main_menu(message, user=db_user)

    except Exception as e:
        logger.error(f"Ошибка при обработке номера телефона {phone_number} для {tg_user.id}: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обработке номера телефона. Попробуйте позже.")

#@registration_required
@auth_router.message(F.text == "👤 Профиль")
@auth_router.callback_query(F.data == "back_to_profile") # Кнопки «Назад»
async def profile(
    event: Message | CallbackQuery,
    #state: FSMContext,
    user_service: UserService,  # — из ServicesMiddleware
    user # — из RegistrationCheckMiddleware
):
    """Показывает профиль пользователя с информацией и статистикой"""

    rating_stars = "★" * int(user.rating) + "☆" * (5 - int(user.rating))
    # Формируем сообщение профиля
    profile_message = (
        "👤 <b>Личный кабинет</b>\n\n"
        f"Пользователь: {user.full_name or 'Не указан'}\n"
        # f"Статус: {'👑 Премиум' if user_data.get('is_premium', False) else '🔹 Стандарт'}\n"  # нет такого поля в User
        f"ID: #{user.id or 0}\n"
        f"Телефон: 📱 {user.phone or 'Не указан'} {'⚠️' if not user.phone or user.phone == 'Не указан' else ''}\n"
        f"Email: 📧 {user.email or 'Не указано'} {'⚠️' if not user.email or user.email == 'Не указан' else ''}\n"
        f"Рейтинг: {'★' * int(user.rating or 5) + '☆' * (5 - int(user.rating or 5))} ({user.rating or 5}/5)\n\n"
        # f"*Рейтинг:* {round(user.rating, 1)} ⭐️ ({user.rating_count} отзывов)\n"

        "📊 <b>Моя статистика:</b>\n"
        # f"• 📦 Сдано вещей в аренду: *{user_data.get('items_rented_out', 0)}*\n"
        # f"• 🧰 Арендовано вещей: *{user_data.get('items_rented', 0)}*\n"
        # f"• 💰 Заработано (ориентировочно): *~{user_data.get('total_earnings', 0)}* ₽\n"
        # f"• 💸 Сэкономлено (ориентировочно): *~{user_data.get('total_savings', 0)}* ₽\n\n"

        "🏆 <b>Достижения:</b>\n"
    )

    # Добавляем достижения
    achievements = [
        # ("Первая сдача", user_data.get("achievement_first_rental_out", False)),
        # ("Первая аренда", user_data.get("achievement_first_rental_in", False)),
        # ("5 сданных вещей", user_data.get("achievement_5_rentals_out", False)),
        # ("5 арендованных вещей", user_data.get("achievement_5_rentals_in", False)),
    ]

    for achievement_name, achieved in achievements:
        checkbox = "☑️" if achieved else "⬜"
        profile_message += f"• {checkbox} {achievement_name}\n"

    profile_message += "\n\nВыберите действие:"

    await send_or_edit(event, profile_message, get_profile_keyboard())

#==================================== Кнопки Профиля ======================================
@auth_router.callback_query(F.data == "profile_stats") # show_statistics
#@auth_router.message(F.text == "📊 Статистика")
async def show_statistics(
    callback: CallbackQuery,
    user,
):
    """Показывает экран статистики пользователя."""

    # Формируем сообщение статистики
    stats_message = (
        "📊 <b>Ваша статистика</b>\n\n"
        f"• 📦 Сдано вещей в аренду: x\n" #*{user_data.get('items_rented_out', 0)}* - x
        f"• 🧰 Арендовано вещей: x\n" #*{user_data.get('items_rented', 0)}* - x
        f"• 💰 Заработано (ориентировочно): x ₽\n" # *~{user_data.get('total_earnings', 0)}* - x
        f"• 💸 Сэкономлено (ориентировочно): x ₽\n\n" # *~{user_data.get('total_savings', 0)}* - x
        # Сюда можно добавить больше статистики в будущем
        # Например, по категориям, по времени и т.д.
    )

    # Кнопка назад
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад в профиль", callback_data="back_to_profile")]
        ]
    )

    await send_or_edit(callback, stats_message, keyboard)
    await callback.answer()

@auth_router.callback_query(F.data == "achievements") # show_achievements
async def show_achievements(
    callback: CallbackQuery,
    user,
):
    """Показывает экран достижений пользователя."""

    # Подготавливаем список достижений (заглушки)


    # Формируем сообщение с достижениями
    achievements_message = "🏆 <b>Ваши достижения</b>\n\n"
    achievements = [  # пока на шару расставил True\False
        ("Первая сдача", True),  # user_data.get("achievement_first_rental_out", False)
        ("Первая аренда", False),  # user_data.get("achievement_first_rental_in", False)
        ("5 сданных вещей", True),  # user_data.get("achievement_5_rentals_out", False)
        ("5 арендованных вещей", False),  # user_data.get("achievement_5_rentals_in", False)
        # Сюда можно добавить больше достижений
        ("10 сделок", True),  # user_data.get("achievement_10_deals", False)
        ("Премиум статус", False),  # user_data.get("is_premium", False)
    ]

    has_achievements = False

    for achievement_name, achieved in achievements:
        if achieved:
            checkbox = "✅" # Используем галочку для полученных
            has_achievements = True
        else:
            checkbox = "⬜" # Используем квадрат для не полученных
        achievements_message += f"• {checkbox} {achievement_name}\n"

    if not has_achievements:
        achievements_message += (
            "\nУ вас пока нет достижений.\n"
            "Совершайте сделки, чтобы их получить!"
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад в профиль", callback_data="back_to_profile")] #profile_back
        ]
    )

    # Отправка результата
    await send_or_edit(callback, achievements_message, keyboard)
    await callback.answer()

@auth_router.callback_query(F.data == "back_to_profile_settings")
@auth_router.callback_query(F.data == "profile_settings") # show_settings
async def show_settings(
    callback: CallbackQuery,
    user,
):
    """Показывает экран настроек пользователя."""

    settings_message = (
        "⚙️ <b>Настройки</b>\n\n"
        "Здесь вы можете изменить параметры вашего аккаунта и уведомлений.\n\n"
        "Выберите раздел настроек:"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔔 Уведомления", callback_data="settings_notifications")],
            [InlineKeyboardButton(text="✏️ Редактировать профиль", callback_data="settings_edit_profile")],
            [InlineKeyboardButton(text="🔒 Конфиденциальность", callback_data="settings_privacy")],
            # Меняем кнопку на возврат в профиль, так как это основной экран настроек
            [InlineKeyboardButton(text="🔙 Назад в профиль", callback_data="back_to_profile")], #profile_back
        ]
    )

    await send_or_edit(callback, settings_message, keyboard)
    await callback.answer()

@auth_router.callback_query(F.data == "profile_change_phone") # change_phone
async def request_phone_number_change(
    callback: CallbackQuery,
    state: FSMContext,
    user,
):
    """Запрашивает новый номер телефона для смены номера в профиле."""

    await callback.answer()

    # Устанавливаем флаг смены номера
    await state.update_data(changing_phone=True)

    text = (
        "📱 <b>Смена номера телефона</b>\n\n"
        "Пожалуйста, нажмите кнопку ниже и поделитесь вашим <b>новым контактом</b>, "
        "чтобы обновить номер телефона в профиле."
    )

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поделиться новым контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    # Показываем пользователю запрос
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

# надо еще кнопку помощи обработать

#====================================Кнопки НАСТРОЕК Профиля======================================

# Уведомления
@auth_router.callback_query(F.data == "settings_notifications")
async def show_notification_settings(
    event: Message | CallbackQuery,
    user,
    user_service: UserService,
):
    """Показывает экран настроек уведомлений (только inline)."""

    # 📌 Текущий статус уведомлений берем из DB (в реальном проекте!)
    # Пока у пользователя нет поля — делаем заглушку в коде.
    notifications_enabled = True   # TODO: добавить в модель User поле notifications_enabled

    """"# user
    # user_data = context.user_data.get("user", {})
    
    # Получаем текущий статус уведомлений (по умолчанию True)
    # Также инициализируем его в user_data, если его там нет
    if "notifications_enabled" not in user_data:
        user_data["notifications_enabled"] = True
    notifications_enabled = user_data.get("notifications_enabled", True)
   """

    # 📘 Формируем текст и кнопку в зависимости от статуса
    if notifications_enabled:
        status_text = "<b>Включены</b> ✅"
        btn_text = "🔕 Выключить уведомления"
        btn_callback = "toggle_notifications:off"
    else:
        status_text = "<b>Выключены</b> ❌"
        btn_text = "🔔 Включить уведомления"
        btn_callback = "toggle_notifications:on"

    # 📄 Формируем сообщение
    text = (
        "⚙️ <b>Настройки уведомлений</b>\n\n"
        f"Текущий статус: {status_text}\n\n"
        "Вы будете получать уведомления о:\n"
        "• новых запросах на аренду\n"
        "• статусах сделок\n"
        "• сообщениях от арендаторов\n"
        "• важных изменениях в профиле\n"
    )

    # 📌 Inline-кнопки
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=btn_text, callback_data=btn_callback)],
            [InlineKeyboardButton(text="« Назад", callback_data="back_to_settings")], # "🔙 Назад в настройки"
        ]
    )

    # 📌 Определяем, как ответить — message или callback
    await send_or_edit(event, text, keyboard)
    await event.answer() # ?

# Редактирование профиля
@auth_router.callback_query(F.data == "settings_edit_profile")
async def show_edit_profile_settings(
    event: Message | CallbackQuery,
    user,
    user_service: UserService,
):
    """Показывает подменю редактирования профиля: имя, email, и т.д."""

    # 📝 Текст сообщения
    text = (
        "✏️ <b>Редактирование профиля</b>\n\n"
        "<b>Текущие данные:</b>\n"
        f"👤 Имя: <b>{user.full_name or 'Не указано'}</b>\n"
        f"📧 Email: <b>{user.email or 'Не указан'}</b>\n\n"
        "Выберите поле для редактирования:"
    )

    # Создаем клавиатуру
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить имя", callback_data="edit_profile_field:name")],
            [InlineKeyboardButton(text="📧 Изменить Email", callback_data="edit_profile_field:email")],
            #[InlineKeyboardButton(text="📱 Изменить телефон", callback_data="edit_profile_field:phone")],  # Пока не делаем
            [InlineKeyboardButton(text="« Назад", callback_data="back_to_settings")],
        ]
    )

    # 💬 Определяем способ ответа
    await send_or_edit(event, text, keyboard)
    await event.answer()

# Конфиденциальность
@auth_router.callback_query(F.data == "settings_privacy")
async def show_privacy_settings(
    callback: CallbackQuery,
    user,
):
    """Показывает экран настроек конфиденциальности."""

    # ✏️ Текст
    message_text = (
        "🔒 <b>Настройки конфиденциальности</b>\n\n"
        "Мы серьёзно относимся к вашей конфиденциальности.\n"
        "Здесь вы можете ознакомиться с нашей политикой.\n\n"
        "В будущем здесь появятся настройки видимости вашего профиля и данных."
        # Сюда можно добавить переключатели для видимости телефона, email и т.д.
    )

    # 🔘 Клавиатура
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📄 Политика конфиденциальности",
                callback_data="show_privacy_policy"
            )],
            #[InlineKeyboardButton(
            #    text="Видимость профиля",
            #    callback_data="privacy_visibility"
            #)],
            [InlineKeyboardButton(
                text="🔙 Назад в настройки",
                callback_data="back_to_settings"
            )]
        ]
    )

    # ✏️ Безопасное редактирование
    await send_or_edit(callback, message_text, keyboard)
    await callback.answer()

#====================================Кнопки ИЗМЕНЕНИЯ======================================

# УВЕДОМЛЕНИЙ
#@auth_router.callback_query(F.data == "toggle_notifications:on")
#async def toggle_notifications(callback, user, enable=True):

#@auth_router.callback_query(F.data == "toggle_notifications:off")
#async def toggle_notifications(callback, user, enable=False):

"""@registration_required
async def toggle_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    #elif callback_data.startswith("toggle_notifications:")
    notif_type = callback_data.split(":")[1] if len(callback_data.split(":")) > 1 else None

    if notif_type in ["new_rentals", "messages", "reviews", "promos"]:
        # Инвертируем текущее состояние уведомления
        if "notifications" not in context.user_data:
            context.user_data["notifications"] = {}

        # Инвертируем значение (по умолчанию True, если ключа нет)
        context.user_data["notifications"][notif_type] = not context.user_data["notifications"].get(notif_type,
                                                                                                    True)

        # Сохраняем настройки в БД
        try:
            from db.all_models import update_user_notification_setting
            update_user_notification_setting(user_id, notif_type, context.user_data["notifications"][notif_type])
        except Exception as e:
            logger.error(f"Не удалось обновить настройки уведомлений: {e}")

        # Повторно показываем настройки уведомлений
        from handlers.auth import show_notification_settings
        await show_notification_settings(update, context)
        return ConversationHandler.END
"""

# ПРОФИЛЯ
@auth_router.callback_query(F.data == "edit_profile_field:name")
async def ask_new_name(callback: CallbackQuery, state: FSMContext):
    #await state.update_data(editing_field_profile="name")  # editing_field="name"  # флаг
    await state.set_state(ProfileEditStates.waiting_for_name)
    # Запрашиваем новое имя
    return await callback.message.edit_text(
        "👤 <b>Изменение имени</b>\n\n"
        "Введите новое имя. Это имя будет отображаться другим пользователям.\n",
        reply_markup=profile_settings_back_keyboard(),
        parse_mode="HTML",
    )

@auth_router.callback_query(F.data == "edit_profile_field:email")
async def ask_new_email(callback: CallbackQuery, state: FSMContext):
    #await state.update_data(editing_field_profile="email")  # editing_field="email"  # флаг
    await state.set_state(ProfileEditStates.waiting_for_email)
    return await callback.message.edit_text(
        "📧 <b>Изменение email</b>\n\n"
        "Введите новый email (Email используется для отправки уведомлений о сделках)",
        reply_markup=profile_settings_back_keyboard(),
        parse_mode="HTML",
    )

@auth_router.message(ProfileEditStates.waiting_for_name)
async def process_edit_name(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    #user,
):
    """Обрабатывает ввод нового имени пользователя (редактирование профиля)"""

    data = await state.get_data()
    if data.get("editing_field_profile") != "name":
        return   # пользователь не находится в процессе редактирования имени

    new_name = message.text.strip()

    if not new_name:
        await message.answer("⚠️ Имя не может быть пустым. Пожалуйста, введите имя.")
        return

    # Получаем пользователя из БД вручную (миддлваре здесь НЕ работает)
    tg_id = message.from_user.id
    user = await user_service.get_by_telegram_id(tg_id)
    if not user:
        await message.answer("❌ Пользователь не найден. Повторите /start.")
        return

    # обновлённый full_name
    full_name = f"{user.first_name or ''} {new_name}".strip()

    try:
        # Обновление в БД через сервис
        updated = await user_service.update(
            user.id,
            UserUpdate(
                last_name=new_name,
                full_name=full_name
            )
        )

        if not updated:
            await message.answer("⚠️ Не удалось сохранить имя. Попробуйте позже.")
            return

        await message.answer(
            f"✅ Ваше имя успешно изменено на <b>{new_name}</b>.",
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"[EditName] Ошибка обновления имени {user.id}: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при сохранении имени.")
        return

    # снимаем флаг редактирования
    await state.update_data(editing_field_profile=None)

    # показываем обновлённый профиль
    await message.answer(
        "🔙 Возвращаемся в профиль...",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Открыть профиль", callback_data="back_to_profile")]
            ]
        )
    )

@auth_router.message(ProfileEditStates.waiting_for_email)
async def process_edit_email(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    #user,
):
    """Обрабатывает ввод нового email. Работает только если FSM находится в режиме редактирования email."""

    # Проверяем, что мы вообще в режиме редактирования
    data = await state.get_data()
    if data.get("editing_field_profile") != "email":
        return     # пользователь написал текст не в тот момент → игнор

    new_email = message.text.strip()

    # Проверка корректности email
    EMAIL_REGEX = r"[^@]+@[^@]+\.[^@]+"
    if not re.match(EMAIL_REGEX, new_email):
        await message.answer(
            "⚠️ Пожалуйста, введите корректный email.\n"
            "Пример: example@mail.com"
        )
        return  # флаг остаётся, пользователь может повторить ввод

    # Получаем пользователя из БД вручную (миддлваре здесь НЕ работает)
    tg_id = message.from_user.id
    user = await user_service.get_by_telegram_id(tg_id)
    if not user:
        await message.answer("❌ Пользователь не найден. Повторите /start.")
        return

    try:
        # Сохраняем в базе
        updated = await user_service.update(
            user.id,
            UserUpdate(email=new_email)
        )

        if not updated:
            await message.answer(
                "⚠️ Не удалось сохранить email. Попробуйте позже."
            )
            return

    except Exception as e:
        logger.error(f"[EditEmail] Ошибка обновления email пользователя {user.id}: {e}")
        await message.answer("❌ Произошла ошибка при сохранении email.")
        return

    # Успех
    await message.answer(
        f"✅ Ваш email успешно обновлён на <b>{new_email}</b>.",
        parse_mode="HTML"
    )

    # Снимаем флаг редактирования
    await state.update_data(editing_field_profile=None)

    # Возврат в профиль
    await message.answer(
        "🔙 Возвращаем вас в профиль...",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(
                text="Открыть профиль",
                callback_data="back_to_profile"
            )]]
        )
    )

# конфиденциальность
@auth_router.callback_query(F.data == "show_privacy_policy")
async def send_privacy_policy(
    callback: CallbackQuery,
    user,
):
    """Показывает текст политики конфиденциальности"""

    privacy_text = (
        "*Политика конфиденциальности*\n\n"
        "🔒 Мы ценим вашу приватность и обязуемся защищать ваши персональные данные.\n\n"
        "Мы собираем только необходимую информацию для работы сервиса:\n"
        "- Ваш Telegram ID и имя пользователя\n"
        "- Контактный номер телефона\n"
        "- Email (по желанию)\n"
        "- Информацию о вещах, которые вы размещаете\n"
        "- Местоположение для поиска вещей (только город/район)\n\n"

        "🛡 *Как мы используем ваши данные:*\n"
        "- Для обеспечения работы сервиса аренды\n"
        "- Для связи между арендодателями и арендаторами\n"
        "- Для улучшения пользовательского опыта\n\n"

        "📱 *Номер телефона* используется только для подтверждения личности и не передается третьим лицам без вашего согласия.\n\n"

        "⚠️ *Важно:* Никогда не передавайте свои персональные данные другим пользователям вне нашего сервиса."
    )

    try:
        await callback.message.edit_text(
            privacy_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🔙 Назад в настройки",
                        callback_data="back_to_settings"
                    )]
                ]
            )
        )
    except TelegramBadRequest:
        # fallback — если нельзя редактировать сообщение
        await callback.message.answer(
            privacy_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🔙 Назад в настройки",
                        callback_data="back_to_settings"
                    )]
                ]
            )
        )

    await callback.answer()