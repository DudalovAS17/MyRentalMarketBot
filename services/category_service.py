import logging
from typing import Optional, List

from db.repositories.category import CategoryRepository
from schemas.category import CategoryOut
from utils.errors import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


def _validate_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise ValidationError("Название категории не может быть пустым")
    return normalized

class CategoryService:
    """Сервис для работы с категориями и подкатегориями"""

    def __init__(self, repo: CategoryRepository) -> None:
        self.repo = repo

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────
    async def list_main_categories(self) -> List[CategoryOut]:
        """Вернуть все категории без подкатегорий (parent_id = NULL)"""
        cats = await self.repo.list_roots()
        return [CategoryOut.model_validate(c) for c in cats]

    async def list_subcategories(self, category_id: int, *, strict: bool = False) -> List[CategoryOut]:
        """Вернуть все подкатегории для категории"""
        if strict:
            parent_cat = await self.repo.get_by_id(category_id)
            if not parent_cat:
                raise NotFoundError(f"Категория не найдена: id={category_id}")

        subs = await self.repo.list_subcategories(category_id)
        return [CategoryOut.model_validate(s) for s in subs]

    async def get_category(self, category_id: int, *, strict: bool = False) -> Optional[CategoryOut]:
        """Вернуть категорию по id"""
        cat = await self.repo.get_by_id(category_id)
        if not cat:
            if strict:
                raise NotFoundError(f"Category not found: id={category_id}")
            return None

        return CategoryOut.model_validate(cat)

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────
    # Admin-only writes (логируем как admin action / бизнес-событие)

    async def create(self, name: str, parent_id: Optional[int] = None) -> CategoryOut:
        """Создать категорию или подкатегорию"""
        normalized_name = _validate_name(name)

        obj = await self.repo.create(name=normalized_name, parent_id=parent_id)
        dto = CategoryOut.model_validate(obj)
        logger.info("Category created id=%s parent_id=%s", dto.id, parent_id)
        return dto

    async def update(
            self,
            category_id: int,
            name: Optional[str] = None,
            emoji: Optional[str] = None,
            *,
            strict: bool = False
    ) -> Optional[CategoryOut]:
        """Обновить категорию или подкатегорию"""
        normalized_name: Optional[str] = None
        if name is not None:
            normalized_name = _validate_name(name)

        obj = await self.repo.update(category_id, name=normalized_name, emoji=emoji)
        if not obj:
            if strict:
                raise NotFoundError(f"Категория не найдена: id={category_id}")
            return None

        dto = CategoryOut.model_validate(obj)
        logger.info("Category updated id=%s", dto.id)
        return dto

    async def delete(self, category_id: int, *, strict: bool = False) -> bool:
        """Удалить категорию или подкатегорию"""
        deleted = await self.repo.delete(category_id)
        if not deleted:
            if strict:
                raise NotFoundError(f"Категория не найдена: id={category_id}")
            return False
        logger.info("Category deleted id=%s", category_id)
        return True