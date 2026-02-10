from pydantic import BaseModel, Field, AwareDatetime, ConfigDict
from typing import Optional, Dict, Any
from decimal import Decimal

from db.models.item import ItemStatus

class ItemCreate(BaseModel):
    """Схема для создания объявления"""

    category_id: int
    subcategory_id: Optional[int] = None
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0) # цена ≥ 0
    deposit: Optional[Decimal] = Field(None, ge=0) # залог ≥ 0
    min_rental_period: int = Field(1, ge=1)  # минимум 1 день
    max_rental_period: Optional[int] = None
    location: Optional[str] = None
    coordinates: Optional[Dict[str, Any]] = None

    # is_available: bool = True # объявление создаётся как is_available=True автоматически -> убираем

    # Это админские поля, не пользовательские -> убираем из Create
    # is_featured: bool = False
    # status: ItemStatus = ItemStatus.PENDING

    #photos: Optional[List[str]] = None  # ?

class ItemUpdate(BaseModel):
    """Схема для обновления объявления (только изменяемые поля)"""

    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    deposit: Optional[Decimal] = Field(None, ge=0)
    min_rental_period: Optional[int] = Field(None, ge=1)
    max_rental_period: Optional[int] = None
    location: Optional[str] = None
    coordinates: Optional[Dict[str, Any]] = None
    is_available: Optional[bool] = None

# Все админские поля вынесем сюда:
class ItemModerationUpdate(BaseModel):
    """Для Админов - схема для обновления объявления"""
    is_featured: Optional[bool] = None
    status: Optional[ItemStatus] = None
    moderation_reason: Optional[str] = None

    # Ставятся сервисом автоматически - убираем
    # moderated_by_admin_id: Optional[int] = None
    # moderated_at: Optional[datetime] = None

""" Если
class ItemModerationUpdate(ItemUpdate): (все поля из ItemUpdate тут тоже будут - унаследовали)

То админ может менять всё, что может пользователь (title/price/…), но пока сделаем чтобы не мог.
"""

class ItemOut(BaseModel):
    """Схема для возврата данных об объявлении"""

    id: int
    user_id: int
    category_id: int
    subcategory_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0)
    deposit: Optional[Decimal] = None
    location: Optional[str] = None
    coordinates: Optional[Dict[str, Any]] = None
    min_rental_period: int = None
    max_rental_period: Optional[int] = None
    is_available: bool = True
    status: ItemStatus
    views_count: int
    orders_count: int
    created_at: AwareDatetime # Optional[datetime] = None
    updated_at: AwareDatetime # Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ItemAdminOut(ItemOut): # все поля из ItemOut тут тоже будут - унаследовали
    is_featured: Optional[bool] = None
    moderated_at: Optional[AwareDatetime] = None
    moderated_by_admin_id: Optional[int] = None
    moderation_reason: Optional[str] = None


