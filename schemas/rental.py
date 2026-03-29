from typing import Optional
from datetime import datetime
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
    start_date: datetime # AwareDatetime
    end_date: datetime # AwareDatetime
    total_price: Decimal = Field(..., ge=0)
    deposit_amount: Optional[Decimal] = Field(None, ge=0)
    status: RentalStatus = RentalStatus.REQUESTED


class RentalUpdate(BaseModel):
    """Схема для обновления сделки (только изменяемые поля)"""
    start_date: Optional[datetime] = None # [AwareDatetime]
    end_date: Optional[datetime] = None # [AwareDatetime]
    total_price: Optional[Decimal] = Field(default=None, ge=0)
    deposit_amount: Optional[Decimal] = Field(default=None, ge=0)
    status: Optional[RentalStatus] = None


class RentalOut(BaseModel):
    """Схема для возврата сделки наружу"""
    id: int
    item_id: int
    renter_id: int
    owner_id: int
    start_date: AwareDatetime # datetime
    end_date: AwareDatetime # datetime
    total_price: Decimal
    deposit_amount: Optional[Decimal]
    status: RentalStatus
    owner_handover_confirmed: bool
    renter_receive_confirmed: bool
    created_at: AwareDatetime # Optional[datetime] = None # [AwareDatetime]
    updated_at: AwareDatetime # Optional[datetime] = None # [AwareDatetime]
    # AwareDatetime - datetime, у которого ОБЯЗАТЕЛЬНО есть tz_info (т.е. timezone-aware)

    model_config = ConfigDict(from_attributes=True)


class RentalWithRoleOut(RentalOut):
    user_role: RentalActorRole


class RentalDetailsOut(BaseModel):
    id: int
    rental: RentalOut
    item: ItemOut
    renter: UserOut
    owner: UserOut
    user_role: RentalActorRole

    model_config = ConfigDict(from_attributes=True)


class RentalAdminDetailsOut(BaseModel):
    rental: RentalOut
    item: ItemOut
    renter: UserOut
    owner: UserOut

    model_config = ConfigDict(from_attributes=True)


class RentalCreateDraft(BaseModel):
    """
    FSM-черновик для создания сделки аренды.
    Поля совпадают с RentalCreate, но start/end/total могут быть пустыми до выбора дат.
    """
    model_config = ConfigDict(extra="forbid")

    item_id: Optional[int] = None
    renter_id: Optional[int] = None
    owner_id: Optional[int] = None

    start_date: Optional[str] = None # "DD.MM.YYYY"
    end_date: Optional[str] = None # "DD.MM.YYYY"

    #start_date: Optional[datetime] = None
    #end_date: Optional[datetime] = None

    total_price: Optional[Decimal] = Field(default=None, ge=0)
    deposit_amount: Optional[Decimal] = Field(default=None, ge=0)

    status: RentalStatus = RentalStatus.REQUESTED