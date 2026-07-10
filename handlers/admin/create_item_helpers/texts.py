from .common import format_money_value, format_photos_count
from .validate import short_description

from utils.validators import format_days
from schemas.item import ItemCreateDraft, ItemOut
from utils.callbacks import MAX_PHOTOS

not_cat_id = "⚠️ Не удалось распознать категорию."
serv_err_cat = "⚠️ Не удалось загрузить категорию. Попробуйте позже."
not_cat = "⚠️ Категория не найдена"

not_subcat_id = "⚠️ Не удалось распознать товар."
serv_err_subcat = "⚠️ Не удалось загрузить подкатегорию. Попробуйте позже."
not_subcat = "⚠️ Подкатегория не найдена"

not_item_id = "⚠️ Не удалось распознать товар."
not_item = "⚠️ Товар не найдено"
serv_err_item = "⚠️ Не удалось загрузить товар. Попробуйте позже."

no_photos = ("⚠️ Вы не загрузили ни одной фотографии.\n"
            "Вы можете продолжить, но товар будет без фото.")
photo_or_ready = ("❌ Пожалуйста, отправьте фотографию.\n"
             "Или нажмите «Готово».")

data_item_not_found = "❌ Данные товары не найдены. Начните создание заново."
cant_create_item_err = "❌ Не удалось создать товар. Попробуйте позже."
draft_item_valid_err = "❌ Данные товары повреждены. Начните создание заново."
# ❌ Произошла ошибка при создании товары. Попробуйте позже.

create_item_valid_err = "❌ Товар заполнено не полностью или содержит ошибки.\n Проверьте поля и попробуйте снова."

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def create_item_category_step_text() -> str:
    """Сформировать текст шага выбора категории"""
    return "📦 <b>Добавить товар</b>\n\nВыберите категорию для вашего товара:"

def create_item_subcategory_step_text(category_name) -> str:
    """Сформировать текст шага выбора подкатегории"""
    return (
        f"📦 <b>Выбор категории для товара</b>\n\n"
        f"Выбрана категория: <b>{category_name}</b>\n"
        f"Уточните подкатегорию:"
    )

def not_subcats(category_name) -> str:
    """Сформировать текст предупреждения"""
    return f"⚠️ В категории <b>{category_name}</b> пока нет подкатегорий."

def create_new_item_text(category, subcategory) -> str:
    """Сформировать текст начала добавления товара"""
    cat_text = f"Категория: <b>{category.name}</b>\n" if category else ""
    subcat_text = f"Подкатегория: <b>{subcategory.name}</b>\n" if subcategory else ""
    return (
        "📦 <b>Новый товар</b>\n\n"
        f"{cat_text}{subcat_text}\n"
        "📝 Введите название товара:"
    )

def build_item_description_step_text() -> str:
    """Сформировать текст шага ввода описания"""
    return (
        "📋 <b>Описание товара</b> ✍️\n\n"
        "Пожалуйста, введите подробное описание товара. Укажите:\n"
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

def build_item_available_quantity_step_text() -> str:
    """Сформировать текст шага ввода доступного количества товара."""
    return (
        "📦 <b>Доступное количество</b>\n\n"
        "Укажите количество единиц товара, которое компания может сдавать в аренду.\n"
        "Введите целое число от 1 и выше.\n\n"
        "💡 Например: 2"
    )

def build_item_min_period_step_text() -> str:
    """Сформировать текст шага ввода минимального срока аренды"""
    return ("⏱️ <b>Отлично!</b>\n\n"
            "Теперь укажите <b>минимальный срок аренды</b>.\n"
            "Например: <code>1 день</code>, <code>3 часа</code>, <code>2 недели</code>.")

def build_item_photo_step_text() -> str:
    """Сформировать текст шага загрузки фотографий"""
    return ("📸 Теперь загрузите фотографии товара.\n"
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
    """Сформировать текст preview товара перед публикацией"""
    title = draft.title or "Без названия"
    description = short_description(draft.description, 120)

    price = format_money_value(draft.price)
    #deposit = format_deposit_value(draft.deposit)

    #location = draft.location or "Не указано"
    min_rental_period = draft.min_rental_period # or 0
    min_rental_period_text = f"{min_rental_period} {format_days(min_rental_period)}"

    photos_text = format_photos_count(photos_count)

    return (
        f"📦 <b>Проверьте товар перед добавлением</b>\n\n"
        f"📝 <b>Название:</b> {title}\n"
        f"🏷️ <b>Категория:</b> {category_name}\n"
        f"📂 <b>Подкатегория:</b> {subcategory_name}\n"
        f"📋 <b>Описание:</b> {description}\n"
        f"💰 <b>Цена:</b> {price} ₽/день\n"
        #f"🔐 <b>Залог:</b> {deposit} ₽\n"
        #f"📍 <b>Местоположение:</b> {location}\n"
        f"⏱️ <b>Мин. срок аренды:</b> {min_rental_period_text}\n"
        f"📸 <b>Фото:</b> {photos_text}\n\n"
        f"Всё верно? Подтвердите добавление товара 👇"
    )

def build_item_created_success_text(title: str) -> str:
    """Сформировать текст успешного добавления товара"""
    return (
        f"✅ Товар <b>«{title}»</b> успешно создан.\n\n"
        "Товар добавлен в каталог аренды. "
        "Менеджеры смогут использовать его при обработке заявок."
    )

def edit_item_start_text(item: ItemOut) -> str:
    """Сформировать стартовый текст редактирования товара"""
    safe_title = item.title or "Без названия"
    return (
        "✏️ <b>Редактирование товара</b>\n\n"
        f"Выберите, что вы хотите изменить в <b>«{safe_title}»</b>:"
    )