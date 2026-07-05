import logging
from typing import Optional

from db.repositories.category import CategoryRepository
from schemas.category import CategoryOut
from utils.errors import NotFoundError
from utils.validators import validate_name

logger = logging.getLogger(__name__)

class CategoryService:
    """Сервис для работы с категориями и подкатегориями каталога компании."""

    def __init__(self, repo: CategoryRepository) -> None:
        self.repo = repo

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _to_out(category) -> CategoryOut:
        return CategoryOut.model_validate(category)

    @classmethod
    def _to_out_list(cls, categories) -> list[CategoryOut]:
        return [cls._to_out(category) for category in categories]

    # ────────────────────────────────────────── Read methods ──────────────────────────────────────────────────────────
    async def list_main_categories(self) -> list[CategoryOut]:
        """Вернуть все категории без подкатегорий (parent_id = NULL)"""
        categories = await self.repo.list_roots()
        return self._to_out_list(categories)

    async def list_subcategories(self, category_id: int, *, strict: bool = False) -> list[CategoryOut]:
        """Вернуть все подкатегории для категории"""
        if strict:
            parent_cat = await self.repo.get_by_id(category_id)
            if not parent_cat:
                raise NotFoundError(f"Категория не найдена: id={category_id}")

        subs = await self.repo.list_subcategories(category_id)
        return self._to_out_list(subs)

    async def get_public_category_by_id(self, category_id: int, *, strict: bool = False) -> Optional[CategoryOut]:
        """Вернуть активную категорию/подкатегорию для клиентского каталога."""
        cat = await self.repo.get_public_by_id(category_id)
        if not cat:
            if strict:
                raise NotFoundError(f"Категория не найдена или скрыта: id={category_id}")
            return None

        return self._to_out(cat)

    async def get_category_by_id(self, category_id: int, *, strict: bool = False) -> Optional[CategoryOut]:
        """Вернуть категорию по id"""
        cat = await self.repo.get_by_id(category_id)
        if not cat:
            if strict:
                raise NotFoundError(f"Категория не найдена: id={category_id}")
            return None

        return self._to_out(cat)

    # ─────────────────────────────────────────── Admin write methods ──────────────────────────────────────────────────
    async def create(
            self,
            name: str,
            *,
            emoji: Optional[str] = None,
            parent_id: Optional[int] = None,
            sort_order: int = 0,
            is_active: bool = True,
            slug: Optional[str] = None,
    ) -> CategoryOut:
        """Создать категорию или подкатегорию"""
        normalized_name = validate_name(name)

        if parent_id is not None:
            parent_cat = await self.repo.get_by_id(parent_id)
            if not parent_cat:
                raise NotFoundError(f"Родительская категория не найдена: id={parent_id}")

        category = await self.repo.create(
            name=normalized_name,
            emoji=emoji,
            parent_id=parent_id,
            sort_order=sort_order,
            is_active=is_active,
            slug=slug,
        )

        dto = self._to_out(category)
        logger.info("Создана категория: id=%s parent_id=%s", dto.id, parent_id)
        return dto

    async def delete(self, category_id: int, *, strict: bool = False) -> bool:
        """Удалить категорию или подкатегорию"""
        deleted = await self.repo.delete(category_id)
        if not deleted:
            if strict:
                raise NotFoundError(f"Категория не найдена: id={category_id}")
            return False

        logger.info("Категория удалена: id=%s", category_id)
        return True