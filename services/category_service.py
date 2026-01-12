import logging
from typing import Optional, List #, Dict, Any

#from db.models.category import Category
from db.repositories.category import CategoryRepository
from schemas.category import CategoryOut

logger = logging.getLogger(__name__)


class CategoryService:
    """Сервис для работы с категориями и подкатегориями"""

    def __init__(self, repo: CategoryRepository) -> None:
        self.repo = repo

    async def list_main(self) -> List[CategoryOut]: # Dict[str, Any]
        """Вернуть все категории без подкатегорий (parent_id = NULL)"""
        cats = await self.repo.list_roots() #  list_roots() приходит в виде:
        # [<Category id=1 name="Электроника" parent_id=None>, <Category id=2 name="Одежда" parent_id=None>]
        # Это не словари, а Python-объекты SQLAlchemy
        # return [c.to_dict() for c in cats] # to_dict() - DictMixin (объект модели в словарь (берёт все колонки таблицы))
        # Итог: [{"id": 1, "name": "Электроника", "parent_id": None},{"id": 2, "name": "Одежда", "parent_id": None}]

        return [CategoryOut.model_validate(c) for c in cats]
        # → [CategoryOut(id=1, name="Электроника", ...), CategoryOut(id=2, name="Одежда", ...)] ← Pydantic-модели

    async def list_subcategories(self, category_id: int) -> List[CategoryOut]:
        """Вернуть все подкатегории для категории"""
        subs = await self.repo.get_subcategories(category_id)
        return [CategoryOut.model_validate(s) for s in subs] # s.to_dict()

    async def get_category(self, category_id: int) -> Optional[CategoryOut]:
        """Вернуть категорию по id"""
        cat = await self.repo.get_by_id(category_id)
        return CategoryOut.model_validate(cat) if cat else None # cat.to_dict()

    async def create(self, name: str, parent_id: Optional[int] = None) -> Optional[CategoryOut]:
        """Создать категорию или подкатегорию"""
        obj = await self.repo.create(name=name, parent_id=parent_id)
        return CategoryOut.model_validate(obj) if obj else None # obj.to_dict()

    async def update(self, category_id: int, name: Optional[str] = None, emoji: Optional[str] = None) \
            -> Optional[CategoryOut]:
        """Обновить категорию или подкатегорию"""
        obj = await self.repo.update(category_id, name=name, emoji=emoji)
        return CategoryOut.model_validate(obj) if obj else None

    async def delete(self, category_id: int) -> bool:
        """Удалить категорию или подкатегорию"""
        return bool(await self.repo.delete(category_id))

"""
    def initialize_defaults(self) -> None:
        ""Наполнить БД стандартными категориями""
        logger.info("TODO: Реализовать предзаполнение категорий")
"""
