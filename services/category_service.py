#import logging
from typing import Optional, List

from db.repositories.category import CategoryRepository
from schemas.category import CategoryOut

#logger = logging.getLogger(__name__)


class CategoryService:
    """Сервис для работы с категориями и подкатегориями"""

    def __init__(self, repo: CategoryRepository) -> None:
        self.repo = repo

    async def list_main(self) -> List[CategoryOut]:
        """Вернуть все категории без подкатегорий (parent_id = NULL)"""
        cats = await self.repo.list_roots()
        return [CategoryOut.model_validate(c) for c in cats]

    async def list_subcategories(self, category_id: int) -> List[CategoryOut]:
        """Вернуть все подкатегории для категории"""
        subs = await self.repo.list_subcategories(category_id)
        return [CategoryOut.model_validate(s) for s in subs]

    async def get_category(self, category_id: int) -> Optional[CategoryOut]:
        """Вернуть категорию по id"""
        cat = await self.repo.get_by_id(category_id)
        return CategoryOut.model_validate(cat) if cat else None

    async def create(self, name: str, parent_id: Optional[int] = None) -> Optional[CategoryOut]:
        """Создать категорию или подкатегорию"""
        obj = await self.repo.create(name=name, parent_id=parent_id)
        return CategoryOut.model_validate(obj) if obj else None

    async def update(self, category_id: int, name: Optional[str] = None, emoji: Optional[str] = None) \
            -> Optional[CategoryOut]:
        """Обновить категорию или подкатегорию"""
        obj = await self.repo.update(category_id, name=name, emoji=emoji)
        return CategoryOut.model_validate(obj) if obj else None

    async def delete(self, category_id: int) -> bool:
        """Удалить категорию или подкатегорию"""
        return bool(await self.repo.delete(category_id))


    """
    async def create_category_idempotent(
        self,
        *,
        name: str,
        emoji: Optional[str],
        parent_id: Optional[int],
    ) -> Category:
        name = name.strip()
    
        existing = await self._category_repo.get_by_name_within_parent(
            name=name, parent_id=parent_id
        )
        if existing:
            return existing
    
        try:
            return await self._category_repo.create(name=name, emoji=emoji, parent_id=parent_id)
        except IntegrityError:
            # гонка: кто-то создал между get и create
            existing = await self._category_repo.get_by_name_within_parent(
                name=name, parent_id=parent_id
            )
            if existing:
                return existing
            raise
    """