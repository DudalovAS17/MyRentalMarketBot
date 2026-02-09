
# ------------------------------------ Модель-Rental --------------------------------------------------
"""
Почему убираем to_dict() и repr():

Правильный проф-подход:
    сериализация → в Pydantic (RentalOut)
    форматирование/JSON → в helpers/formatters

Что сделать быстро:
    to_dict()
    repr()
"""

# Используется для логов, отладочных сообщений, консоли разработчика -> logger.info(rental)
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
json.dumps(rental) → выдаст ошибку.
"""
# -----------------------------------------------------------------------------------------------------------