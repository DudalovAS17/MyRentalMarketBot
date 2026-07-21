from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, AwareDatetime, ConfigDict

from schemas.item import ItemOut
from schemas.user import UserOut
from status.rental_status import RentalStatus


"""
    RentalCreate        → клиент создаёт заявку
    RentalUpdate        → менеджер/система обновляет заявку
    RentalOut           → базовый вывод заявки
    RentalDetailsOut    → заявка + товар + клиент
    RentalAdminDetailsOut → админский подробный вывод   
    RentalCreateDraft   → FSM-черновик пошагового создания
    
    RentalCreateInternal → внутренний service payload с рассчитанной стоимостью
    RentalStatusUpdate  → внутреннее обновление статуса и timestamp-полей
"""

class RentalCreate(BaseModel):
    """Клиентская схема для создания заявки на аренду товара."""

    item_id: int
    user_id: int

    total_price: Optional[Decimal] = Field(None, ge=0)

    #start_date: Optional[AwareDatetime] = None
    #end_date: Optional[AwareDatetime] = None
    rental_period_text: Optional[str] = Field(None, max_length=100)

    quantity: int = Field(1, ge=1)

    delivery_needed: Optional[bool] = None
    delivery_address: Optional[str] = None

    client_name: Optional[str] = Field(None, max_length=150)
    client_phone: Optional[str] = Field(None, max_length=30)
    client_comment: Optional[str] = None


class RentalUpdate(BaseModel):
    """Схема для обновления заявки на аренду менеджером или системой."""

    #start_date: Optional[AwareDatetime] = None
    #end_date: Optional[AwareDatetime] = None
    rental_period_text: Optional[str] = Field(default=None, max_length=100)

    total_price: Optional[Decimal] = Field(default=None, ge=0)
    final_price: Optional[Decimal] = Field(default=None, ge=0)

    status: Optional[RentalStatus] = None
    quantity: Optional[int] = Field(default=None, ge=1)

    delivery_needed: Optional[bool] = None
    delivery_address: Optional[str] = None
    client_name: Optional[str] = Field(default=None, max_length=150)
    client_phone: Optional[str] = Field(default=None, max_length=30)
    client_comment: Optional[str] = None

    manager_comment: Optional[str] = None
    reject_reason: Optional[str] = None
    cancel_reason: Optional[str] = None

    assigned_admin_id: Optional[int] = None

    in_progress_at: Optional[AwareDatetime] = None
    processed_at: Optional[AwareDatetime] = None
    closed_at: Optional[AwareDatetime] = None
    confirmed_at: Optional[AwareDatetime] = None
    rejected_at: Optional[AwareDatetime] = None
    cancelled_at: Optional[AwareDatetime] = None
    completed_at: Optional[AwareDatetime] = None


class RentalOut(BaseModel):
    """Схема для возврата заявки на аренду наружу."""
    id: int
    item_id: int
    user_id: int

    #start_date: Optional[AwareDatetime] = None
    end_date: Optional[AwareDatetime] = None

    rental_period_text: Optional[str] = None
    total_price: Optional[Decimal] = None
    final_price: Optional[Decimal] = None

    status: RentalStatus
    quantity: int

    delivery_needed: Optional[bool] = None
    delivery_address: Optional[str] = None
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    client_comment: Optional[str] = None

    manager_comment: Optional[str] = None
    reject_reason: Optional[str] = None
    cancel_reason: Optional[str] = None

    assigned_admin_id: Optional[int] = None
    in_progress_at: Optional[AwareDatetime] = None
    processed_at: Optional[AwareDatetime] = None
    closed_at: Optional[AwareDatetime] = None
    confirmed_at: Optional[AwareDatetime] = None
    rejected_at: Optional[AwareDatetime] = None
    cancelled_at: Optional[AwareDatetime] = None
    completed_at: Optional[AwareDatetime] = None

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)


# ────────────────────────────────────────── Rental Details ────────────────────────────────────────────────────────────
# class RentalWithRoleOut(RentalOut): user_role: RentalActorRole


class RentalDetailsOut(BaseModel):
    """Полная информация о заявке: заявка, товар и клиент."""

    rental: RentalOut
    item: ItemOut
    user: UserOut

    model_config = ConfigDict(from_attributes=True)


# ────────────────────────────────────────── Rental Admin Details ──────────────────────────────────────────────────────
class RentalAdminDetailsOut(BaseModel):
    """Полная информация о заявке для администратора/менеджера."""

    rental: RentalOut
    item: ItemOut
    user: UserOut

    model_config = ConfigDict(from_attributes=True)


# ────────────────────────────────────────── Rental Draft ──────────────────────────────────────────────────────────────
class RentalCreateDraft(BaseModel):
    """FSM-черновик для пошагового создания заявки на аренду."""

    model_config = ConfigDict(extra="forbid")

    item_id: Optional[int] = None

    #start_date: Optional[str] = None
    #end_date: Optional[str] = None

    rental_period_text: Optional[str] = Field(default=None, max_length=100)
    quantity: Optional[int] = Field(default=None, ge=1)


    delivery_needed: Optional[bool] = None
    delivery_address: Optional[str] = Field(default=None, max_length=300)

    client_name: Optional[str] = Field(default=None, max_length=150)
    client_phone: Optional[str] = Field(default=None, max_length=30)
    client_comment: Optional[str] = Field(default=None, max_length=1000)

    # Убрал это, т.к. ниже создан отдельный класс для работы с ценой
    #total_price: Optional[Decimal] = Field(default=None, ge=0)


# ──────────────────────────────────────────  ──────────────────────────────────────────────────────────────
class RentalCreateInternal(RentalCreate):
    """Внутренний payload создания заявки после service-level расчёта стоимости."""

    total_price: Optional[Decimal] = Field(default=None, ge=0)


class RentalStatusUpdate(BaseModel):
    """Внутреннее обновление статуса заявки через service-level transition method."""

    status: RentalStatus
    manager_comment: Optional[str] = Field(default=None, max_length=1000)
    reject_reason: Optional[str] = Field(default=None, max_length=1000)
    cancel_reason: Optional[str] = Field(default=None, max_length=1000)

