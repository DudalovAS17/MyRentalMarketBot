from typing import Optional


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
    "Формируется автоматически при заключении заявки и содержит все необходимые условия аренды.\n\n"

    "💼 Полные тексты документов будут предоставлены по запросу."
)

# Помощь при команде /help
HELP_TEXT = (
    "🔍 <b>Как пользоваться ботом</b>\n\n"
    "<b>Основные команды:</b>\n"
    "✅ /start - Запуск бота и показ главного меню\n"
    "🔍 /search - Поиск товаров для аренды\n"
    "🤝 /rentals - Просмотр моих заявок\n"
    "👤 /profile - Просмотр личного профиля\n"
    "📜 /legal - Юридическая информация\n"
    "❓ /help - Вывод этой справки\n"
    "❌ /cancel - Отмена текущей операции\n\n"

    "<b>Как арендовать оборудование:</b>\n"
    "1️⃣ Нажмите '🔍 Арендовать' в главном меню или используйте команду /search\n"
    "2️⃣ Выберите категорию или воспользуйтесь поиском по городу\n"
    "3️⃣ Просмотрите доступные товары\n"
    "4️⃣ Выберите подходящее товары\n"
    "5️⃣ Нажмите кнопку 'Арендовать' и следуйте инструкциям\n\n"

    "<b>Управление арендой:</b>\n"
    "В разделе '📋 Мои аренды' вы можете:\n"
    "- 📋 Просматривать активные и завершенные аренды\n"
    "- ✅ Подтверждать передачу и возврат товаров\n"
    "- ⭐ Оставлять отзывы после завершения аренды\n\n"

    "📱 По всем вопросам обращайтесь в раздел '📞 Поддержка'"
)

# ─────────────────────────────────────────────────unknown_command──────────────────────────────────────────────────────
# Словарь с соответствиями неправильных команд правильным
COMMAND_SUGGESTIONS = {
    # Команды для сделок
    "/мои заявки": "/rentals",
    "/заявки": "/rentals",
    "/аренды": "/rentals",
    "/rentals": "/rentals",

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

    # Команды для товаров
    "/товар": "/items",
    "/мое оборудование": "/items",
    "/мои товары": "/items",
    "/items": "/items",

    # Команды для старта
    "/старт": "/start",
    "/начать": "/start",
    "/перезапуск": "/start"
}

UNKNOWN_COMMAND_BASE_TEXT = (
    "⚠️ Я не понимаю эту команду.\n"
    "Используйте /help для просмотра доступных команд."
)

MAIN_COMMANDS_TEXT = (
    "\n\n🔹 Основные команды:\n"
    "/start — Главное меню\n"
    "/search — Поиск товаров\n"
    "/rentals — Мои заявки\n"
    "/profile — Профиль\n"
    "/help — Справка"
)

SEMANTIC_COMMAND_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("профиль", "аккаунт"), "Используйте команду /profile для просмотра вашего профиля."),
    (("поиск", "найти", "искать"), "Используйте команду /search для поиска оборудования в аренду."),
    (("товар", "оборудование", "товары"), "Используйте команду /items для просмотра ваших товаров"),
    (("заявк", "аренд"), "Используйте команду /rentals для просмотра ваших заявок."),
    (("помощь", "справка", "инструкция"), "Используйте команду /help для получения справки."),
)

def _get_command_suggestion(command: Optional[str]) -> str:
    # Получаем правильную команду или None
    command_lower = _normalize_command(command)
    if command_lower in COMMAND_SUGGESTIONS:
        correct_command = COMMAND_SUGGESTIONS[command_lower]
        return f"Используйте команду {correct_command}"

    # Попытка найти похожую команду
    for wrong, correct in COMMAND_SUGGESTIONS.items():
        wrong_text = _strip_command_prefix(wrong)
        command_text = _strip_command_prefix(command_lower)

        if wrong_text in command_text or command_text in wrong_text:
            return f"Возможно, вы имели в виду команду {correct}"

    # Если подсказка не найдена, предлагаем общие команды
    for keywords, suggestion in SEMANTIC_COMMAND_HINTS:
        if any(keyword in command_lower for keyword in keywords):
            return suggestion

    return ""

def _normalize_command(command: Optional[str]) -> str:
    """ Получаем правильную команду или ""
    " /Start " → "/start"
    "/PROFILE" → "/profile"
    None → ""
    """
    if not command:
        return ""

    normalized = command.strip().lower()
    if not normalized:
        return ""

    return normalized

def _strip_command_prefix(command: str) -> str:
    """Убирает начальный / у команды"""
    return command[1:] if command.startswith("/") else command

def build_unknown_command_text(command: Optional[str]) -> str:
    suggestion = _get_command_suggestion(command)

    if not suggestion:
        return UNKNOWN_COMMAND_BASE_TEXT + MAIN_COMMANDS_TEXT

    return f"{UNKNOWN_COMMAND_BASE_TEXT}\n\n💡 {suggestion}{MAIN_COMMANDS_TEXT}"

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
