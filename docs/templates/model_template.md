# Template: ORM Model

## Правила:
- Только ORM-описание таблиц и связей
- Никакой бизнес-логики/Telegram/FSM
- Идентификаторы: db_user_id vs telegram_user_id
    * db_user_id: FK на users.id (внутренний ID БД)
    * telegram_user_id: внешний ID Telegram


```
from __future__ import annotations

from typing import Optional
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base, DictMixin, ReprMixin, TimestampMixin

class Example(Base, TimestampMixin, ReprMixin, DictMixin):
    """ORM-модель Example"""
    
    __tablename__ = "examples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    db_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), 
        nullable=False,
    )
    
    telegram_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        nullable=True,
    )

    # пример связи
    user: Mapped["User"] = relationship("User", back_populates="examples")

    __table_args__ = (
        Index("ix_examples_db_user_id", "db_user_id"),
        Index("ix_examples_telegram_user_id", "telegram_user_id"),
    )
```
---

### **ForeignKey("users.id", ondelete="RESTRICT")**

❌ Запрещает удалить строку из users, если на неё есть ссылки в этой таблице

- RESTRICT = «не трогай, если есть история»   (История / финансы / сделки)
- CASCADE = 🔥 удаляет всё связанное	(временные данные)
- SET NULL	= ставит NULL	мягкие связи (мягкие связи)
- NO ACTION	= зависит от БД	редко

---

### **Два разных механизма создания индексов**
- mapped_column(..., index=True)
- __table_args__ = (Index("ix_xxx_field", "field"))

Если оставить оба:
* SQLAlchemy создаст ДВА индекса
* один с автогенерированным именем
* второй с явным именем

👉 Это непрофессионально и ведёт к мусору в БД.

*Решение - не используем index=True*
*Вместо него - __table_args__ = Index()*