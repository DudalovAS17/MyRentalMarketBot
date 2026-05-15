from .common import get_items_count_str, format_money_value, format_deposit_value, format_photos_count
from .validate import short_description

from utils.functions import format_days, format_price
from schemas.item import ItemCreateDraft, ItemOut
from utils.callbacks import MAX_PHOTOS

not_cat_id = "⚠️ Не удалось распознать категорию."
serv_err_cat = "⚠️ Не удалось загрузить категорию. Попробуйте позже."
not_cat = "⚠️ Категория не найдена"

not_subcat_id = "⚠️ Не удалось распознать подкатегорию."
serv_err_subcat = "⚠️ Не удалось загрузить подкатегорию. Попробуйте позже."
not_subcat = "⚠️ Подкатегория не найдена"

not_item_id = "⚠️ Не удалось распознать объявление."
not_item = "⚠️ Объявление не найдено"
serv_err_item = "⚠️ Не удалось загрузить объявление. Попробуйте позже."

# ─────────────────────────────────────────────────show─────────────────────────────────────────────────────────────────
def my_items_screen_text(count: int) -> str:
    """Сформировать текст экрана списка моих объявлений"""
    if count == 0:
        return (
            "📦 <b>Мои объявления</b>\n\n"
            "У вас пока нет активных объявлений.\n"
            "Создайте новое объявление, чтобы сдать вещи в аренду!"
        )

    return (
        "📦 <b>Мои объявления</b>\n\n"
        f"У вас {count} {get_items_count_str(count)}.\n"
        "Выберите объявление для просмотра или редактирования:"
    )

def item_details_text(item: ItemOut, category_name: str, subcategory_name: str) -> str:
    """Сформировать текст карточки объявления"""
    title = item.title or "Без названия"
    description = item.description or "Описание не указано"
    location = item.location or "Не указано"
    min_rental_period = item.min_rental_period or 1
    deposit_text = f"{format_price(item.deposit)} ₽" if item.deposit else "Без залога"
    #availability_text = "✅ Доступно для аренды" if item.is_available else "❌ Временно недоступно"

    return (
        f"📦 <b>{title}</b>\n\n"
        f"📝 <b>Описание:</b>\n{description}\n\n"
        f"🏷️ <b>Категория:</b> {category_name} > {subcategory_name}\n" # {category_name or '-'}
        f"💰 <b>Цена:</b> {format_price(item.price)} ₽/день\n"
        f"🕒 <b>Минимальный срок аренды:</b> {min_rental_period} {format_days(min_rental_period)}\n"
        f"🔐 <b>Залог:</b> {deposit_text}\n"
        f"📍 <b>Местоположение:</b> {location}\n"
        #f"👤 <b>Владелец:</b> {item.user_id}\n"
        #f"⭐ <b>Рейтинг:</b> ... ({item.views_count} отзывов)\n"
        #f"✅ <b>Доступность:</b> {availability_text}\n\n"
    )

# ─────────────────────────────────────────────────flow_create──────────────────────────────────────────────────────────
no_photos = ("⚠️ Вы не загрузили ни одной фотографии.\n"
            "Вы можете продолжить, но объявление будет без фото.")

photo_or_ready = ("❌ Пожалуйста, отправьте фотографию.\n"
             "Или нажмите «Готово».")

data_item_not_found = "❌ Данные объявления не найдены. Начните создание заново."
cant_create_item_err = "❌ Не удалось создать объявление. Попробуйте позже."
draft_item_valid_err = "❌ Данные объявления повреждены. Начните создание заново."
# ❌ Произошла ошибка при создании объявления. Попробуйте позже.

create_item_valid_err = "❌ Объявление заполнено не полностью или содержит ошибки.\n Проверьте поля и попробуйте снова."

def create_item_category_step_text() -> str:
    """Сформировать текст шага выбора категории"""
    return "📦 <b>Сдать в аренду</b>\n\nВыберите категорию для вашего объявления:"

def create_item_subcategory_step_text(category_name) -> str:
    """Сформировать текст шага выбора подкатегории"""
    return (
        f"📦 <b>Выбор категории для объявления</b>\n\n"
        f"Выбрана категория: <b>{category_name}</b>\n"
        f"Уточните подкатегорию:"
    )

def create_new_item_text(category, subcategory) -> str:
    """Сформировать текст начала создания объявления"""
    cat_text = f"Категория: <b>{category.name}</b>\n" if category else ""
    subcat_text = f"Подкатегория: <b>{subcategory.name}</b>\n" if subcategory else ""
    return (
        "📦 <b>Ваше новое объявление</b>\n\n"
        f"{cat_text}{subcat_text}\n"
        "📝 Введите название вещи:"
    )

def build_item_description_step_text() -> str:
    """Сформировать текст шага ввода описания"""
    return (
        "📋 <b>Описание объявления</b> ✍️\n\n"
        "Пожалуйста, введите подробное описание вещи. Укажите:\n"
        "- Состояние и особенности\n"
        "- Комплектацию\n"
        "- Особенности использования\n"
        "- Другую важную информацию"
    )

def build_item_price_step_text() -> str:
    """Сформировать текст шага ввода цены аренды"""
    return ("💰 <b>Цена аренды</b>\n\n"
            "Укажите стоимость аренды за один день (только число).\n"
            "Например: 500") # "Укажите стоимость аренды в формате '500 руб/день' или '100 руб/час':"

def build_item_deposit_step_text() -> str:
    """Сформировать текст шага ввода залога"""
    return ("🔐 <b>Залог</b>\n\n"
            "Укажите сумму залога (только число).\n"
            "💡 Залог возвращается после возврата вещи в исходном состоянии.\n"
            "Например: 5000")

def build_item_location_step_text() -> str:
    """Сформировать текст шага ввода местоположения"""
    return ("📍 <b>Местоположение</b>\n\n"
            "Укажите, где находится вещь (город, район, метро и т.д.).\n"
            "Эта информация будет видна потенциальным арендаторам.")

def build_item_min_period_step_text() -> str:
    """Сформировать текст шага ввода минимального срока аренды"""
    return ("⏱️ <b>Отлично!</b>\n\n"
            "Теперь укажите <b>минимальный срок аренды</b>.\n"
            "Например: <code>1 день</code>, <code>3 часа</code>, <code>2 недели</code>.")

def build_item_photo_step_text() -> str:
    """Сформировать текст шага загрузки фотографий"""
    return ("📸 Теперь загрузите фотографии вещи.\n"
            "Можно загрузить до 5 штук.\n"
            "Когда закончите — нажмите <b>«Готово»</b>.")

def build_item_photo_max_photos_warning() -> str:
    """Сформировать предупреждение о лимите фотографий"""
    return (f"⚠️ Вы уже загрузили максимальное количество фотографий ({MAX_PHOTOS}).\n"
           f"Нажмите «Готово», чтобы продолжить.")

def build_item_photo_success_or_more(len_photos) -> str:
    """Сформировать текст успешной загрузки фото"""
    return (f"📸 Фото загружено! ({len_photos}/{MAX_PHOTOS})\n"
        f"Отправьте ещё фото (вы можете загрузить еще {MAX_PHOTOS - len_photos})"
        "или нажмите «✅ Готово».")

def build_item_confirmation_text(draft: ItemCreateDraft, category_name: str, subcategory_name: str, photos_count: int) -> str:
    """Сформировать текст preview объявления перед публикацией"""
    title = draft.title or "Без названия"
    description = short_description(draft.description, 120)

    price = format_money_value(draft.price)
    deposit = format_deposit_value(draft.deposit)

    location = draft.location or "Не указано"
    min_rental_period = draft.min_rental_period # or 0
    min_rental_period_text = f"{min_rental_period} {format_days(min_rental_period)}"

    photos_text = format_photos_count(photos_count)

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

def build_item_created_success_text(title: str) -> str:
    """Сформировать текст успешного создания объявления"""
    return (
        f"✅ <b>Поздравляем!</b>\n\n"
        f"Ваше объявление <b>«{title}»</b> успешно создано.\n\n"
        "Сейчас объявление отправлено на модерацию, появится после одобрения, "
        "и его увидят другие пользователи в поиске. "
        "Когда кто-то захочет арендовать вашу вещь — вы получите уведомление."
    )

def edit_item_start_text(item: ItemOut) -> str:
    """Сформировать стартовый текст редактирования объявления"""
    safe_title = item.title or "Без названия"
    return (
        "✏️ <b>Редактирование объявления</b>\n\n"
        f"Выберите, что вы хотите изменить в <b>«{safe_title}»</b>:"
    )