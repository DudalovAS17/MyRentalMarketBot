
# ------------------------------------ Модель-Rental --------------------------------------------------
"""
Почему убираем to_dict() и repr():

Правильный проф-подход:
    сериализация → в Pydantic (RentalOut)
    форматирование/JSON → в item_helpers/formatters

Что сделать быстро:
    to_dict()
    repr()
"""

# Используется для логов, отладочных сообщений, консоли разработчика -> logger.info(rentals)
def __repr__(self) -> str:
    return (
        f"<Rental id={self.id} item_id={self.item_id} "
        f"renter_id={self.renter_id} owner_id={self.owner_id} "
        f"status={getattr(self.status, 'value', self.status)}>" # Безопасно извлекает строковое значение из Enum
    )  # <Rental id=7 item_id=33 renter_id=10 owner_id=4 status=requested>

# Превращает SQLAlchemy-модель → обычный Python-словарь (приводит их к JSON-friendly виду)
def to_dict(self) -> dict[str, Any]:
    """Тут status, даты, деньги, остальные — обычные питоновские типы"""
    d = DictMixin.to_dict(self) # Базовое преобразование ORM → dict
    """
    - берутся все поля модели
    - превращаются в словарь вида:
        {"id": 1, "status": RentalStatus.REQUESTED, "start_date": datetime(...), 
        "total_price": Decimal("1000.00"), ...}
    ⚠️ Типы всё ещё “опасные” — Enum, datetime, Decimal.
    """

    # Enum -> str
    d["status"] = self.status.value if isinstance(self.status, enum.Enum) else self.status
    # Status — это Enum (RentalStatus.REQUESTED и т. п.)
    # Пример: RentalStatus.REQUESTED → "requested"

    # isinstance(self.status, enum.Enum) - Это проверка типа:
    # является ли self.status экземпляром любого Enum (если да → True, если нет → False)

    # datetime -> ISO-строка
    for k in ("start_date", "end_date", "created_at", "updated_at"): # это все datetime
        if isinstance(d.get(k), datetime):
            d[k] = d[k].isoformat()
    # datetime(2024, 1, 1, 12, 30) → "2024-01-01T12:30:00" (стандартный JSON-friendly формат дат)

    # Decimal -> str (или float, но лучше не надо: float → риск округлений = теряется точность денег)
    for m in ("total_price", "deposit_amount"):  # это все Decimal
        if isinstance(d.get(m), Decimal):
            d[m] = str(d[m])
    # Пример: Decimal("1000.00") → "1000.00"

    return d  # Возвращаем словарь уже в «JSON-дружелюбном» виде: строки вместо Enum и дат


"""
SQLAlchemy-модель содержит данные, которые нельзя сохранить в JSON:
- enum.Enum
- datetime
- Decimal

Без преобразования:
json.dumps(rentals) → выдаст ошибку.
"""

""" ❌ Миксины ReprMixin, DictMixin — нарушение “чистоты ORM”

Почему это проблема:
    - DictMixin почти гарантированно тянет to_dict() / сериализацию
    - ReprMixin часто делает “умный repr” (иногда даже с доменной логикой)

👉 Даже если ты сейчас уберёшь to_dict() из Rental, сам факт наличия DictMixin/ReprMixin — уже конфликт с законом.
Как должно быть по законам:
В ORM остаются только “табличные” миксины (например TimestampMixin с колонками).

Всё сериализационное и “красивое” — в DTO/formatters.
"""
# ----------------------------------------------------------------------------------------------------------

# ------------------------------------ Модель-Category -----------------------------------------------------
def __repr__(self) -> str:
    return f"<Category id={self.id} name={self.name!r} parent_id={self.parent_id}>"


def to_dict(self) -> dict:
    return {
        "id": self.id,
        "name": self.name,
        "emoji": self.emoji,
        "parent_id": self.parent_id,
    }
# ----------------------------------------------------------------------------------------------------------

# ------------------------------------ Модель-Item ---------------------------------------------------------
def to_dict(self) -> dict:
    return {
        "id": self.id,
        "user_id": self.user_id,
        "category_id": self.category_id,
        "subcategory_id": self.subcategory_id,
        "title": self.title,
        "description": self.description,
        "price": self.price,
        "deposit": self.deposit,
        "location": self.location,
        "coordinates": self.coordinates,
        "is_available": self.is_available,
        "is_featured": self.is_featured,
        "min_rental_period": self.min_rental_period,
        "max_rental_period": self.max_rental_period,
        "views_count": self.views_count,
        "orders_count": self.orders_count,
        "created_at": self.created_at,
        "updated_at": self.updated_at
    }
# ----------------------------------------------------------------------------------------------------------

# ------------------------------------ Модель-User ---------------------------------------------------------
@property
def display_name(self) -> str:
    if self.full_name:
        return self.full_name
    if self.first_name or self.last_name:
        return f"{self.first_name or ''} {self.last_name or ''}".strip()
    return self.username or self.telegram_id
# ----------------------------------------------------------------------------------------------------------

# ------------------------------------ Модель-Admin ---------------------------------------------------------

def to_dict(self) -> dict:
    return {
        "id": self.id,
        "admin_id": self.admin_id,
        "action_type": self.action_type,
        "entity_type": self.entity_type,
        "entity_id": self.entity_id,
        "note": self.note,
        "payload": self.payload,
        "created_at": getattr(self, "created_at", None),
    }
# -------------------------------------------------------------------------------------------------------------------

# ------------------------------------ Модель-SupportTicket ---------------------------------------------------------
def __repr__(self) -> str:
    return (
        f"<SupportTicket id={self.id} user_id={self.user_id} "
        f"status={getattr(self.status, 'value', self.status)}>"
    )

def to_dict(self) -> dict[str, Any]:
    d = DictMixin.to_dict(self)

    # # Enum -> str
    d["status"] = self.status.value if isinstance(self.status, enum.Enum) else self.status # else d.get("status")

    # datetime -> ISO
    for k in ("created_at", "updated_at", "closed_at", "admin_last_reply_at"):
        if isinstance(d.get(k), datetime):
            d[k] = d[k].isoformat()

    return d
# -------------------------------------------------------------------------------------------------------------------

# ------------------------------------ Главная Модель ---------------------------------------------------------------
class ReprMixin:
    """ModelName(id=1, ...). Показывает PK и пару полей"""
    def __repr__(self) -> str:
        mapper = sa_inspect(self).mapper
        keys = [col.key for col in mapper.primary_key] or [c.key for c in mapper.column_attrs[:2]] # PK или, если нет — первые 2 колонки
        parts = []
        for k in keys:
            try:
                parts.append(f"{k}={getattr(self, k)!r}")
            except Exception:
                pass
        return f"<{self.__class__.__name__} " + ", ".join(parts) + ">"

class DictMixin:
    """to_dict() для всех колонок без связей """
    def to_dict(self) -> dict[str, Any]:
        mapper = sa_inspect(self).mapper
        return {c.key: getattr(self, c.key) for c in mapper.column_attrs}