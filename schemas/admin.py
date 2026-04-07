from typing import Optional
from pydantic import BaseModel, AwareDatetime, ConfigDict

class AdminActionCreate(BaseModel):
    """Схема для записи audit-действия админа (создание)"""

    admin_tg_id: int # tg_id, не user_id
    action_type: str
    entity_type: str
    entity_id: str

    note: Optional[str] = None # Короткая человеко-читаемая заметка (опционально)
    payload: Optional[dict] = None # Optional[dict[str, Any]] # Детали (reason/resolution/previous_status/metadata)

class AdminActionOut(BaseModel):
    """Схема для возврата audit-записи наружу."""
    id: int
    admin_tg_id: int
    action_type: str
    entity_type: str
    entity_id: str

    note: Optional[str] = None
    payload: Optional[dict] = None # Optional[dict[str, Any]]

    created_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)