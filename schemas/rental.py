from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, AwareDatetime, ConfigDict

from schemas.item import ItemOut
from schemas.user import UserOut
from status.rental_status import RentalActorRole, RentalStatus

class RentalCreate(BaseModel):
    """Схема для создания сделки аренды"""

    item_id: int
    renter_id: int
    owner_id: int
    start_date: AwareDatetime
    end_date: AwareDatetime
    total_price: Decimal = Field(..., ge=0)
    deposit_amount: Optional[Decimal] = Field(None, ge=0)


class RentalUpdate(BaseModel):
    """Схема для обновления сделки (только изменяемые поля)"""

    start_date: Optional[AwareDatetime] = None
    end_date: Optional[AwareDatetime] = None
    total_price: Optional[Decimal] = Field(default=None, ge=0)
    deposit_amount: Optional[Decimal] = Field(default=None, ge=0)
    status: Optional[RentalStatus] = None

class RentalOut(BaseModel):
    """Схема для возврата сделки наружу"""

    id: int
    item_id: int
    renter_id: int
    owner_id: int
    start_date: AwareDatetime
    end_date: AwareDatetime
    total_price: Decimal
    deposit_amount: Optional[Decimal]
    status: RentalStatus
    owner_handover_confirmed: bool
    renter_receive_confirmed: bool
    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)


class RentalWithRoleOut(RentalOut):
    """Схема для возврата сделки наружу с указанием роли текущего пользователя в сделке"""

    user_role: RentalActorRole


class RentalDetailsOut(BaseModel):
    """Схема для возврата полной информации о сделке наружу, включая объявление, арендатора,
    владельца и роль текущего пользователя"""

    id: int
    rental: RentalOut
    item: ItemOut
    renter: UserOut
    owner: UserOut
    user_role: RentalActorRole

    model_config = ConfigDict(from_attributes=True)


class RentalAdminDetailsOut(BaseModel):
    """Схема для возврата полной информации о сделке наружу для администратора"""

    rental: RentalOut
    item: ItemOut
    renter: UserOut
    owner: UserOut

    model_config = ConfigDict(from_attributes=True)


class RentalCreateDraft(BaseModel):
    """ FSM-черновик для создания сделки аренды.

    Поля совпадают с RentalCreate, но start/end/total могут быть пустыми до выбора дат.
    """

    model_config = ConfigDict(extra="forbid")

    item_id: Optional[int] = None
    renter_id: Optional[int] = None
    owner_id: Optional[int] = None

    start_date: Optional[str] = None
    end_date: Optional[str] = None

    total_price: Optional[Decimal] = Field(default=None, ge=0)
    deposit_amount: Optional[Decimal] = Field(default=None, ge=0)