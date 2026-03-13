from __future__ import annotations

from typing import Optional
from sqlalchemy import select, exists, and_

from db.models.category import Category
from db.repositories.base import BaseRepository


class CategoryRepository(BaseRepository):
    """Репозиторий категорий"""
    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    async def list_all(self) -> list[Category]:
        """Получает все категории (с подкатегориями)"""
        async with self._session() as s:
            return await self._list(s, select(Category))

    async def list_roots(self) -> list[Category]:
        """Достает все категории, без подкатегорий. В алфавитном порядке"""
        async with self._session() as s:
            stmt = (
                select(Category)
                .where(Category.parent_id.is_(None))
                .order_by(Category.name) # сортируем по имени (алфавит)
            )
            return await self._list(s, stmt)

    async def get_by_id(self, category_id: int) -> Optional[Category]:
        """Получение категории и подкатегории по ID"""
        async with self._session() as s:
            return await s.get(Category, category_id)

    async def list_subcategories(self, parent_id: int) -> list[Category]:
        """Получение подкатегорий для указанной категории"""
        async with self._session() as s:
            stmt = (
                select(Category)
                .where(Category.parent_id == parent_id)
                #.order_by(Category.name)
            )
            return await self._list(s, stmt)

    # name = name.strip()
    async def get_by_name_within_parent(self, *, name: str, parent_id: Optional[int]) -> Optional[Category]:
        """ Получение категории по имени
        — если parent_id=None: найти категорию по имени;
        — если parent_id=X: найти подкатегорию по имени внутри категории X.
        """
        async with self._session() as s:
            cond = self._name_within_parent_condition(name, parent_id)
            return await self._one_or_none(s, select(Category).where(cond))

    async def exists_by_name_within_parent(self, *, name: str, parent_id: Optional[int]) -> bool:
        """Проверка «есть ли такая запись?»  Когда нужен просто ответ «есть / нет»"""
        async with self._session() as s:
            cond = self._name_within_parent_condition(name, parent_id)
            return await self._exists(s, select(exists().where(cond)))

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def create(self, *, name: str, emoji: Optional[str] = None, parent_id: Optional[int] = None) -> Category:
        """
        — parent_id=None: создать категорию;
        — parent_id=X: создать подкатегорию в категории X.
        (Дубликаты по (parent_id, name) не создаст — вернёт существующую.)
        """
        async with self._session() as s:
            obj = Category(name=name, emoji=emoji, parent_id=parent_id)
            return await self._add_commit_refresh(s, obj)

    async def update(self, category_id: int, *, name: Optional[str] = None, emoji: Optional[str] = None) -> Optional[Category]:
        """переименовать/сменить emoji у категории или подкатегории."""
        async with self._sf() as s:
            obj: Optional[Category] = await s.get(Category, category_id)
            if not obj:
                return None

            changed = False
            if name is not None and name != obj.name: # и если она не пустая, и отличается от текущей
                obj.name = name
                changed = True
            if emoji is not None and emoji != obj.emoji:
                obj.emoji = emoji
                changed = True

            if not changed:
                return obj

            return await self._commit_refresh(s, obj)

    async def delete(self, category_id: int) -> bool:
        """Удалить категорию или подкатегорию (Если удаляешь категорию — её подкатегории тоже уйдут, каскад)
        Возвращает True если удалили, False если не нашли/ошибка."""
        async with self._sf() as s:
            obj = await s.get(Category, category_id)
            if not obj:
                return False

            return await self._delete_commit(s, obj)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _name_within_parent_condition(name: str, parent_id: Optional[int]):
        return and_(
            Category.name == name,
            Category.parent_id.is_(None)
            if parent_id is None
            else Category.parent_id == parent_id,
        )