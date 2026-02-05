## Template: Repository

✅ MVP-стандарт:
- Только SQLAlchemy/DB
- Никакой бизнес-логики
- Возвращает ORM-объекты
- Может принимать DTO/Pydantic как input (но не возвращает DTO)
- exclude_unset=True на update

### ПРИНИМАЕТ / ОТДАЕТ

- get_by_id(...) -> Optional[ORM]
- get_by_* (...) -> Optional[ORM]
- list_* (...) -> list[ORM]
- create(CreateDTO) -> ORM
- update(id, UpdateDTO) -> Optional[ORM]
- delete(id) -> bool


```
import logging
from typing import Callable, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Example
from schemas.example import ExampleCreate, ExampleUpdate

logger = logging.getLogger(__name__)


class ExampleRepository:
    """Репозиторий для работы с Example-моделью.
    SQLAlchemy only
    DI: session_factory -> Session
    Returns ORM
    """

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sf = session_factory

    async def get_by_id(self, example_id: int) -> Optional[Example]:
        """Получить сущность по ID."""
        async with self._sf() as s:
            return await s.get(Example, example_id)

    async def get_by_telegram_id(self, tg_user_id: int | str) -> Optional[Example]:
        """Получить сущность по Telegram ID (как строка в БД)."""
        async with self._sf() as s:
            res = await s.execute(select(Example).where(Example.telegram_user_id == tg_user_id))
            return res.scalar_one_or_none()

    async def create(self, data: ExampleCreate) -> Example:
        """Создать сущность. Возвращает ORM-объект."""
        obj = Example(**data.model_dump())
        async with self._sf() as s:
            s.add(obj)
            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            await s.refresh(obj)
            return obj

    async def update(self, example_id: int, data: ExampleUpdate) -> Optional[Example]:
        """Обновить сущность (только переданные поля)."""
        patch = data.model_dump(exclude_unset=True)
        """
        exclude_unset=True - флаг Pydantic (не включать в результат поля, которые не были переданы пользователем).
        То есть не “равны None”, а именно не были установлены вообще
        
        Пользователь не передал поле - unset
        Пользователь передал - null
        exclude_unset=True сохраняет это различие.
        """
        async with self._sf() as s:
            obj = await s.get(Example, example_id)
            if not obj:
                return None

            if patch:
                for k, v in patch.items():
                    setattr(obj, k, v)
                try:
                    await s.commit()
                except Exception:
                    await s.rollback()
                    raise
                await s.refresh(obj)

            return obj

    async def delete(self, example_id: int) -> bool:
        """Удалить сущность по ID. Возвращает True если удалено, False если не найдено."""
        async with self._sf() as s:
            obj = await s.get(Example, example_id)
            if not obj:
                return False
            await s.delete(obj)
            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            return True
```


**Код с логами**
```
    async def create(self, data: ExampleCreate) -> Example:
        ""Создать сущность. Возвращает ORM-объект.""
        async with self._sf() as s:
            obj = Example(**data.model_dump())
            s.add(obj)

            try:
                await s.commit()
                await s.refresh(obj)
                logger.info("create() — Example created id=%s", obj.id)
                return obj
            except Exception as e:
                await s.rollback()
                logger.error("create() — Example create failed: %s", e, exc_info=True)
                raise

                
    async def update(self, example_id: int, payload: Union[dict, ExampleUpdate]) -> Optional[Example]:
        ""Обновить сущность (только переданные поля).""
        data = payload.model_dump(exclude_unset=True) if isinstance(payload, ExampleUpdate) else payload
        async with self._sf() as s:
            obj = await s.get(Example, example_id)
            if not obj:
                logger.warning("update() — Example id=%s не найден", example_id)
                return None
            for key, value in data.items():
                setattr(obj, key, value)
            try:
                await s.commit()
            except Exception as exc:
                await s.rollback()
                logger.error("update() — ошибка при обновлении Example id=%s: %s", example_id, exc, exc_info=True)
                raise
            await s.refresh(obj)
            return obj
            
            
    async def delete(self, example_id: int) -> int:
        ""Удалить сущность по ID. Возвращает 1 если удалено, 0 если не найдено.""
        async with self._sf() as s:
            obj = await s.get(Example, example_id)
            if not obj:
                logger.warning("delete() — Example id=%s не найден", example_id)
                return 0
            try:
                await s.delete(obj)
                await s.commit()
            except Exception as exc:
                await s.rollback()
                logger.error("delete() — ошибка при удалении Example id=%s: %s", example_id, exc, exc_info=True)
                raise
            return 1
```