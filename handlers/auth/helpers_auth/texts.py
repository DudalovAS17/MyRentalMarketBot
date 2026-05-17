
# ────────────────────────────────────────────────── profile ───────────────────────────────────────────────────────────
def build_profile_text(user) -> str:
    """Сформировать текст экрана профиля"""
    #rating_stars = "★" * int(user.rating) + "☆" * (5 - int(user.rating))
    return  (
        "👤 <b>Личный кабинет</b>\n\n"
        f"Пользователь: {user.full_name or 'Не указан'}\n"
        # f"Статус: {'👑 Премиум' if user_data.get('is_premium', False) else '🔹 Стандарт'}\n"  # нет такого поля в User
        f"ID: #{user.id or 0}\n"
        f"Телефон: 📱 {user.phone or 'Не указан'} {'⚠️' if not user.phone or user.phone == 'Не указан' else ''}\n"
        f"Email: 📧 {user.email or 'Не указано'} {'⚠️' if not user.email or user.email == 'Не указан' else ''}\n"
        f"Рейтинг: {'★' * int(user.rating or 5) + '☆' * (5 - int(user.rating or 5))} ({user.rating or 5}/5)\n\n"
        # f"*Рейтинг:* {round(user.rating, 1)} ⭐️ ({user.rating_count} отзывов)\n"

        f"\n\nВыберите действие:"
    )

def build_profile_stats_text() -> str:
    """Сформировать текст экрана статистики"""
    return (
        "📊 <b>Ваша статистика</b>\n\n"
        f"• 📦 Сдано вещей в аренду: x\n" #*{user_data.get('items_rented_out', 0)}* - x
        f"• 🧰 Арендовано вещей: x\n" #*{user_data.get('items_rented', 0)}* - x
        f"• 💰 Заработано (ориентировочно): x ₽\n" # *~{user_data.get('total_earnings', 0)}* - x
        f"• 💸 Сэкономлено (ориентировочно): x ₽\n\n" # *~{user_data.get('total_savings', 0)}* - x
        # Сюда можно добавить больше статистики в будущем
        # Например, по категориям, по времени и т.д.
    )

def default_achievements() -> list[tuple[str, bool]]:
    """Список достижений-заглушек до подключения реальных данных"""
    return [  # пока на шару расставил True\False
        ("Первая сдача", True),  # user_data.get("achievement_first_rental_out", False)
        ("Первая аренда", False),  # user_data.get("achievement_first_rental_in", False)
        ("5 сданных вещей", True),  # user_data.get("achievement_5_rentals_out", False)
        ("5 арендованных вещей", False),  # user_data.get("achievement_5_rentals_in", False)
        # Сюда можно добавить больше достижений
        ("10 сделок", True),  # user_data.get("achievement_10_deals", False)
        ("Премиум статус", False),  # user_data.get("is_premium", False)
    ]


def build_achievements_text() -> str:
    """Сформировать текст экрана достижений"""
    achievements_message = "🏆 <b>Ваши достижения</b>\n\n"
    achievements = default_achievements()

    has_achievements = False

    for achievement_name, achieved in achievements:
        if achieved:
            checkbox = "☑️" # Используем галочку для полученных
            has_achievements = True
        else:
            checkbox = "⬜" # Используем квадрат для не полученных
        achievements_message += f"• {checkbox} {achievement_name}\n"

    if not has_achievements:
        achievements_message += "\nУ вас пока нет достижений.\nСовершайте сделки, чтобы их получить!"

    return achievements_message

# ────────────────────────────────────────────────── edit profile ──────────────────────────────────────────────────────
EDIT_NAME_FIELD = "name"
EDIT_EMAIL_FIELD = "email"

def build_edit_profile_menu_text(user) -> str:
    return (
        "✏️ <b>Редактирование профиля</b>\n\n"
        "<b>Текущие данные:</b>\n"
        f"👤 Имя: <b>{user.full_name or 'Не указано'}</b>\n"
        f"📧 Email: <b>{user.email or 'Не указан'}</b>\n\n"
        "Выберите поле для редактирования:"
    )

def build_edit_name_prompt_text() -> str:
    return "👤 <b>Изменение имени</b>\n\nВведите новое имя. Это имя будет отображаться другим пользователям.\n"

def build_edit_email_prompt_text() -> str:
    return "📧 <b>Изменение email</b>\n\nВведите новый email (Email используется для отправки уведомлений о сделках)"

def build_profile_name_updated_text(new_name: str) -> str:
    return f"✅ Ваше имя успешно изменено на <b>{new_name}</b>."

def build_profile_email_updated_text(new_email: str) -> str:
    return f"✅ Ваш email успешно обновлён на <b>{new_email}</b>."


# ────────────────────────────────────────────────── phone ─────────────────────────────────────────────────────────────
def build_invalid_contact_text() -> str:
    """Сформировать текст ошибки некорректного контакта."""
    return (
        "⚠️ Пожалуйста, используйте кнопку ниже, чтобы отправить свой реальный контакт.\n\n"
        "Это нужно для подтверждения вашего номера телефона."
    )

def build_phone_changed_success_text(phone_number: str) -> str:
    """Сформировать текст успешной смены телефона."""
    return f"✅ Ваш новый номер сохранён: <b>{phone_number}</b>"

def build_change_phone_prompt_text() -> str:
    """Сформировать prompt смены номера телефона."""
    return (
        "📱 <b>Смена номера телефона</b>\n\n"
        "Пожалуйста, нажмите кнопку ниже и поделитесь вашим <b>новым контактом</b>, "
        "чтобы обновить номер телефона в профиле."
    )

# ───────────────────────────────────────────────── privacy ────────────────────────────────────────────────────────────
def build_privacy_settings_text() -> str:
    """Сформировать текст настроек конфиденциальности."""
    return (
        "🔒 <b>Настройки конфиденциальности</b>\n\n"
        "Мы серьёзно относимся к вашей конфиденциальности.\n"
        "Здесь вы можете ознакомиться с нашей политикой.\n\n"
        "В будущем здесь появятся настройки видимости вашего профиля и данных."
        # Сюда можно добавить переключатели для видимости телефона, email и т.д.
    )

def build_privacy_policy_text() -> str:
    """Сформировать текст политики конфиденциальности."""
    return (
        "<b>Политика конфиденциальности</b>\n\n"
        "🔒 Мы ценим вашу приватность и обязуемся защищать ваши персональные данные.\n\n"
        "Мы собираем только необходимую информацию для работы сервиса:\n"
        "- Ваш Telegram ID и имя пользователя\n"
        "- Контактный номер телефона\n"
        "- Email (по желанию)\n"
        "- Информацию о вещах, которые вы размещаете\n"
        "- Местоположение для поиска вещей (только город/район)\n\n"

        "🛡 <b>Как мы используем ваши данные:</b>\n"
        "- Для обеспечения работы сервиса аренды\n"
        "- Для связи между арендодателями и арендаторами\n"
        "- Для улучшения пользовательского опыта\n\n"

        "📱 <b>Номер телефона</b> используется только для подтверждения личности и не передается третьим лицам без вашего согласия.\n\n"

        "⚠️ <b>Важно:</b> Никогда не передавайте свои персональные данные другим пользователям вне нашего сервиса."
    )

# ───────────────────────────────────────────────── settings ───────────────────────────────────────────────────────────
def build_settings_text() -> str:
    """Сформировать текст главного экрана настроек."""
    return (
        "⚙️ <b>Настройки</b>\n\n"
        "Здесь вы можете изменить параметры вашего аккаунта и уведомлений.\n\n"
        "Выберите раздел настроек:"
    )

def build_notification_settings_text(notifications_enabled: bool) -> str:
    """Сформировать текст настроек уведомлений."""
    status_text = "<b>Включены</b> ✅" if notifications_enabled else "<b>Выключены</b> ❌"

    return (
        "⚙️ <b>Настройки уведомлений</b>\n\n"
        f"Текущий статус: {status_text}\n\n"
        "Вы будете получать уведомления о:\n"
        "• новых запросах на аренду\n"
        "• статусах сделок\n"
        "• сообщениях от арендаторов\n"
        "• важных изменениях в профиле\n"
    )