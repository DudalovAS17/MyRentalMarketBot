# ─────────────────────────────────────────────────1────────────────────────────────────────────────────────────────────
async def _show_create_item_categories_step(
    callback: CallbackQuery, # event: CallbackQuery | Message,
    category_service: CategoryService,
) -> None:
    try:
        categories = await category_service.list_main_categories()
    except ServiceError:
        await send_or_edit(callback, "⚠️ Не удалось загрузить категории. Попробуйте позже.")
        return

    categories = categories or []

    await send_or_edit(
        callback,
        _create_item_category_step_text(),
        markup=_build_create_item_categories_keyboard(categories),
    )

def _build_create_item_categories_keyboard(categories) -> InlineKeyboardMarkup:
    return build_category_keyboard(
        categories,
        prefix=CAT_FI_PREFIX,
        extra_buttons=[
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data=BACK_TO_MENU_CB)]
        ],
    )

def _create_item_category_step_text() -> str:
    return "📦 <b>Сдать в аренду</b>\n\nВыберите категорию для вашего объявления:"

# ─────────────────────────────────────────────────2────────────────────────────────────────────────────────────────────
async def _load_entity_or_notify(
        callback: CallbackQuery,
        loader, # : Callable[[int], Awaitable[T | None]],
        entity_id: int | None,
        invalid_id_text: str,
        load_error_text: str,
        not_found_text: str
): #  -> list[T] | None:
    if entity_id is None:
        await send_or_edit(callback, invalid_id_text)
        return None

    try:
        entity = await loader(entity_id)
    except ServiceError:
        await send_or_edit(callback, load_error_text)
        return None

    if entity is None:
        await send_or_edit(callback, not_found_text)
        return None

    return entity

async def _store_selected_category(state: FSMContext, category) -> None:
    await state.update_data(
        selected_category_id=category.id,
        selected_category_name=category.name,
        # при смене категории логично сбросить подкатегорию
        selected_subcategory_id=None,
        selected_subcategory_name=None,
        #selected_item_id=None,
    )

def _build_create_item_subcategories_keyboard(subcategories) -> InlineKeyboardMarkup:
    return build_category_keyboard(
        subcategories,
        prefix=SUBCAT_FI_PREFIX,
        extra_buttons=[
            [InlineKeyboardButton(text="🔙 Назад (к категориям)", callback_data=BACK_TO_CAT)] # "create_back_to_cat"
        ],
    )

def _create_item_subcategory_step_text(category_name) -> str:
    return (
        f"📦 <b>Выбор категории для объявления</b>\n\n"
        f"Выбрана категория: <b>{category_name}</b>\n"
        f"Уточните подкатегорию:"
    )

# ─────────────────────────────────────────────────3────────────────────────────────────────────────────────────────────
async def _store_selected_subcategory(
    state: FSMContext,
    category,
    subcategory,
    draft: ItemCreateDraft,
) -> None:
    await state.update_data(
        selected_category_id=category.id,
        selected_category_name=category.name,
        selected_subcategory_id=subcategory.id,
        selected_subcategory_name=subcategory.name,
        new_item=draft.model_dump(),
    )

# ─────────────────────────────────────────────────4────────────────────────────────────────────────────────────────────
def _create_new_item_text(category, subcategory) -> str:
    cat_text = f"Категория: <b>{category.name}</b>\n" if category else ""
    subcat_text = f"Подкатегория: <b>{subcategory.name}</b>\n" if subcategory else ""
    return (
        "📦 <b>Ваше новое объявление</b>\n\n"
        f"{cat_text}{subcat_text}\n"
        "📝 Введите название вещи:"
    )

# ─────────────────────────────────────────────────5────────────────────────────────────────────────────────────────────
def _extract_item_text_input(message: Message) -> str:
    return (message.text or "").strip()

def _validate_item_title(title: str) -> str | None:
    if not title:
        return "❌ Название не должно быть пустым. Введите название вещи."
    if len(title) < 3:
        return "❌ Название слишком короткое. Введите не менее 3 символов."
    if len(title) > 255:
        return "❌ Название слишком длинное. Введите не более 255 символов."
    return None

async def _render_create_item_step_message(message: Message, text: str, step: int, total_steps: int = 6) -> None:
    await message.answer(
        format_step(text, step, total_steps),
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )

def _build_item_description_step_text() -> str:
    return (
        "📋 *Описание объявления* ✍️\n\n"
        "Пожалуйста, введите подробное описание вещи. Укажите:\n"
        "- Состояние и особенности\n"
        "- Комплектацию\n"
        "- Особенности использования\n"
        "- Другую важную информацию"
    )

# ─────────────────────────────────────────────────6────────────────────────────────────────────────────────────────────
def _build_item_price_step_text() -> str:
    return ("💰 *Цена аренды*\n\n"
            "Укажите стоимость аренды за один день (только число).\n"
            "Например: 500") # "Укажите стоимость аренды в формате '500 руб/день' или '100 руб/час':"

# тут проверь
def _validate_item_description(description: str) -> str | None:
    if not description:
        return "❌ Описание не должно быть пустым. Введите описание вещи."

    elif len(description) < 10:
        return "❌ Описание слишком короткое. Пожалуйста, введите более подробное описание (минимум 10 символов)"

    return None # ?
# ─────────────────────────────────────────────────7────────────────────────────────────────────────────────────────────
def _extract_item_money_input(message: Message) -> str:
    return (message.text or "").strip().replace(",", ".") # Преобразуем введённое значение в число

async def _validate_item_price(price_text: str) -> tuple[str | None, Decimal | None]:
    try:
        price = Decimal(price_text)
    except (InvalidOperation, ValueError):
        return "❌ Некорректное значение.\nВведите цену — только число, больше 0.", None

    if price <= 0:
        return "❌ Цена должна быть положительным числом.", None

    return None, price

def _build_item_deposit_step_text() -> str:
    return ("🔐 *Залог*\n\n"
            "Укажите сумму залога (только число).\n"
            "💡 Залог возвращается после возврата вещи в исходном состоянии.\n"
            "Например: 5000")

# ─────────────────────────────────────────────────8────────────────────────────────────────────────────────────────────
async def _validate_item_deposit(deposit_text: str) -> tuple[str | None, Decimal | None]:
    try:
        deposit = Decimal(deposit_text)
    except (InvalidOperation, ValueError):
        return "❌ Некорректное значение. Пожалуйста, введите число.", None

    if deposit < 0:
        return "❌ Сумма залога не может быть отрицательной.", None

    return None, deposit

def _build_item_location_step_text() -> str:
    return ("📍 *Местоположение*\n\n"
            "Укажите, где находится вещь (город, район, метро и т.д.).\n"
            "Эта информация будет видна потенциальным арендаторам.")

# ─────────────────────────────────────────────────9────────────────────────────────────────────────────────────────────
def _build_item_min_period_step_text() -> str:
    return ("⏱️ <b>Отлично!</b>\n\n"
            "Теперь укажите <b>минимальный срок аренды</b>.\n"
            "Например: <code>1 день</code>, <code>3 часа</code>, <code>2 недели</code>.")

# ─────────────────────────────────────────────────10───────────────────────────────────────────────────────────────────
async def _validate_item_min_period(rental_period: str) -> tuple[str | None, int | None]:
    try:
        min_days = int(rental_period)
    except ValueError:
        return "❌ Некорректное значение. Введите число дней, например: <code>1</code>.", None

    if min_days < 1:
        return "❌ Минимальный срок аренды должен быть не меньше 1 дня.", None

    return None, min_days

def _build_item_photo_step_text() -> str:
    return ("📸 Теперь загрузите фотографии вещи.\n"
            "Можно загрузить до 5 штук.\n"
            "Когда закончите — нажмите <b>«Готово»</b>.")

# ─────────────────────────────────────────────────11───────────────────────────────────────────────────────────────────
no_photos = ("⚠️ Вы не загрузили ни одной фотографии.\n"
            "Вы можете продолжить, но объявление будет без фото.")

photo_or_ready = ("❌ Пожалуйста, отправьте фотографию.\n"
             "Или нажмите «Готово».")

def _build_item_photo_max_photos_warning() -> str:
    return (f"⚠️ Вы уже загрузили максимальное количество фотографий ({MAX_PHOTOS}).\n"
           f"Нажмите «Готово», чтобы продолжить.")

def _build_item_photo_success_or_more(len_photos) -> str:
    return (f"📸 Фото загружено! ({len_photos}/{MAX_PHOTOS})\n"
        f"Отправьте ещё фото (вы можете загрузить еще {5 - len_photos})"
        "или нажмите «✅ Готово».")

# ─────────────────────────────────────────────────12───────────────────────────────────────────────────────────────────
def _build_item_confirmation_text(
        draft: ItemCreateDraft,
        category_name: str,
        subcategory_name: str,
        photos_count: int,
) -> str:
    title = draft.title or "Без названия"
    description = _short_description(draft.description, 120)

    price = _format_money_value(draft.price)
    deposit = _format_deposit_value(draft.deposit)

    location = draft.location or "Не указано"
    min_rental_period = draft.min_rental_period # or 0
    min_rental_period_text = f"{min_rental_period} {format_days(min_rental_period)}"

    photos_text = _format_photos_count(photos_count)

    return (
        f"📦 <b>Проверьте объявление перед публикацией</b>\n\n"
        f"📝 <b>Название:</b> {title}\n"
        f"🏷️ <b>Категория:</b> {category_name}\n"
        f"📂 <b>Подкатегория:</b> {subcategory_name}\n"
        f"📋 <b>Описание:</b> {description}\n"
        f"💰 <b>Цена:</b> {price} ₽/день\n"
        f"🔐 <b>Залог:</b> {deposit} ₽\n"
        f"📍 <b>Местоположение:</b> {location}\n"
        f"⏱️ <b>Мин. срок аренды:</b> {min_rental_period_text}\n"
        f"📸 <b>Фото:</b> {photos_text}\n\n"
        f"Всё верно? Подтвердите создание объявления 👇"
    )

def _extract_item_confirmation_context(data: dict) -> tuple[str, str, list[str]]:
    category_name = data.get("selected_category_name") or "будет уточнена модератором"
    subcategory_name = data.get("selected_subcategory_name") or "будет уточнена модератором"

    raw_photos: list[str] = data.get("photos") or []
    photos = [photo for photo in raw_photos if isinstance(photo, str) and photo.strip()]

    return category_name, subcategory_name, photos

def _short_description(description: str | None, limit: int = 300) -> str:
    if not description:
        return "Описание не указано"

    cleaned = description.strip()
    if len(cleaned) <= limit:
        return cleaned

    return cleaned[: limit - 3].rstrip() + "..." # не проверял

def _format_money_value(value: Decimal | int | float | None) -> str:
    if value is None:
        return format_price(Decimal("0"))
    return format_price(value)

def _format_deposit_value(value: Decimal | int | float | None) -> str:
    if not value:
        return "Без залога" # Decimal("0")?
    return f"{format_price(value)} ₽"

def _format_photos_count(count: int) -> str:
    if count == 0:
        return "нет фото"
    if count == 1:
        return "1 фото"
    if 2 <= count <= 4:
        return f"{count} фото"
    return f"{count} фото"

def _build_item_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Разместить объявление", callback_data=PUBLISH_ITEM_CB)],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=CANCEL_ITEM_CB)], # BACK_TO_MENU_CB
        ]
    )

async def _send_item_confirmation_preview(
        *,
        message: Message,
        text: str,
        photos: list[str],
        keyboard: InlineKeyboardMarkup,
) -> None:
    if photos:
        try:
            await message.answer_photo(
                photo=photos[0],
                caption=text,
                reply_markup=keyboard,
            )
            return
        except TelegramBadRequest:
            # если caption/фото не прошло — покажем текстом
            pass

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

# ─────────────────────────────────────────────────13───────────────────────────────────────────────────────────────────
def _build_item_created_success_text(title: str) -> str:
    return (
        f"✅ <b>Поздравляем!</b>\n\n"
        f"Ваше объявление <b>«{title}»</b> успешно создано.\n\n"
        "Сейчас объявление отправлено на модерацию, появится после одобрения, "
        "и его увидят другие пользователи в поиске. "
        "Когда кто-то захочет арендовать вашу вещь — вы получите уведомление."
    )

data_item_not_found = "❌ Данные объявления не найдены. Начните создание заново."

cant_create_item_err = "❌ Не удалось создать объявление. Попробуйте позже."

draft_item_valid_err = "❌ Данные объявления повреждены. Начните создание заново."
# ❌ Произошла ошибка при создании объявления. Попробуйте позже.

create_item_valid_err = ("❌ Объявление заполнено не полностью или содержит ошибки.\n"
            "Проверьте поля и попробуйте снова.")

async def _attach_item_photos_or_warn(
    callback: CallbackQuery,
    photo_service: PhotoService,
    item_id: int,
    photos: list[str],
) -> None:
    #valid_photos = [photo for photo in photos if isinstance(photo, str) and photo.strip()]
    #if not valid_photos:
    #    return

    try:
        await photo_service.create_photos(item_id, photos)  # valid_photos
    except ServiceError: # просто предупреждаем пользователя и идём дальше
        if callback.message:
            await callback.message.answer(
                "⚠️ Объявление создано, но фото не удалось сохранить. Попробуйте добавить их позже.",
                parse_mode="HTML",
            )

# ─────────────────────────────────────────────────14───────────────────────────────────────────────────────────────────
async def _init_edit_item_context(state: FSMContext, item) -> None:
    await state.update_data(
        edit_item_id=item.id,
        edit_field=None,
    )

def _edit_item_start_text(item) -> str:
    safe_title = item.title or "Без названия"
    return (
        "✏️ <b>Редактирование объявления</b>\n\n"
        f"Выберите, что вы хотите изменить в <b>«{safe_title}»</b>:"
    )