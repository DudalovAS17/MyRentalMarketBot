from typing import Optional
from pydantic import BaseModel, AwareDatetime, ConfigDict

class AdminActionCreate(BaseModel):
    """Схема для записи audit-действия админа (создание)"""

    admin_tg_id: int
    action_type: str
    entity_type: str
    entity_id: str

    note: Optional[str] = None
    payload: Optional[dict[str, object]] = None

class AdminActionOut(BaseModel):
    """Схема для возврата audit-записи наружу"""

    id: int
    admin_tg_id: int
    action_type: str
    entity_type: str
    entity_id: str

    note: Optional[str] = None
    payload: Optional[dict[str, object]] = None

    created_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)