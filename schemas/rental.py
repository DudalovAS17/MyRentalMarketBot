from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal
from db.models.rental import RentalStatus


class RentalCreate(BaseModel):
    """Схема для создания сделки аренды"""
    item_id: int
    renter_id: int
    owner_id: int
    start_date: datetime
    end_date: datetime
    total_price: Decimal = Field(..., ge=0)
    deposit_amount: Optional[Decimal] = Field(None, ge=0)
    status: RentalStatus = RentalStatus.REQUESTED


class RentalUpdate(BaseModel):
    """Схема для обновления сделки (только изменяемые поля)"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    total_price: Optional[Decimal] = Field(None, ge=0)
    deposit_amount: Optional[Decimal] = Field(None, ge=0)
    status: Optional[RentalStatus] = None


class RentalOut(BaseModel):
    """Схема для возврата сделки наружу"""
    id: int
    item_id: int
    renter_id: int
    owner_id: int
    start_date: datetime
    end_date: datetime
    total_price: Decimal
    deposit_amount: Optional[Decimal]
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
