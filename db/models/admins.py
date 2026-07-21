from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, Boolean, Enum as SAEnum, Index, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin, enum_values
from status.user_status import AccountStatus
from status.admin_status import AdminRole

if TYPE_CHECKING:
    from db.models.item import Item
    from db.models.rental import Rental
    from db.models.support_ticket import SupportTicket
    from db.models.admin_actions import AdminAction


class Admin(Base, TimestampMixin):
    """Админ/менеджер компании"""
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # уникальный телеграм-id
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)

    # профиль
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # какие права у админа
    role: Mapped[AdminRole] = mapped_column(
        SAEnum(AdminRole, name="admin_role", values_callable=enum_values),
        nullable=False,
        default=AdminRole.MANAGER,
    )

    # включён ли доступ к админке
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    account_status: Mapped[AccountStatus] = mapped_column(
        SAEnum(AccountStatus, name="account_status", values_callable=enum_values),
        nullable=False,
        default=AccountStatus.ACTIVE
    )


    # ------- Отношения | связи --------

    created_items: Mapped[list["Item"]] = relationship(
        "Item",
        foreign_keys="Item.created_by_admin_id",
        back_populates="created_by_admin",
    )

    updated_items: Mapped[list["Item"]] = relationship(
        "Item",
        foreign_keys="Item.updated_by_admin_id",
        back_populates="updated_by_admin",
    )

    closed_support_tickets: Mapped[list["SupportTicket"]] = relationship(
        "SupportTicket",
        foreign_keys="SupportTicket.closed_by_admin_id",
        back_populates="closed_by_admin",
    )

    admin_actions: Mapped[list["AdminAction"]] = relationship("AdminAction", back_populates="admin")

    assigned_rentals: Mapped[list["Rental"]] = relationship(
        "Rental",
        foreign_keys="Rental.assigned_admin_id",
        back_populates="assigned_admin",
    )

    __table_args__ = (
        Index("ix_admins_account_status", "account_status"),
        Index("ix_admins_username", "username"),
        Index("ix_admins_role", "role"),
        Index("ix_admins_is_active", "is_active"),
    )