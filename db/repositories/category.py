from __future__ import annotations

from typing import Callable, Optional, List
from sqlalchemy import select, exists, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.category import Category


class CategoryRepository:
    """Репозиторий категорий"""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sf = session_factory

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    async def list_all(self) -> List[Category]:
        """Получает все категории (с подкатегориями)"""
        async with self._sf() as s:
            res = await s.execute(select(Category))
            return list(res.scalars())

    async def list_roots(self) -> List[Category]:
        """Достает все категории, без подкатегорий. В алфав-м порядке"""
        async with self._sf() as s:
            stmt = (
                select(Category)
                .where(Category.parent_id.is_(None))
                .order_by(Category.name) # сортируем по имени (алфавит)
            )
            res = await s.execute(stmt)
            return list(res.scalars())

    async def get_by_id(self, category_id: int) -> Optional[Category]:
        """Получение категории и подкатегории по ID"""
        async with self._sf() as s:
            return await s.get(Category, category_id)

    async def list_subcategories(self, parent_id: int) -> List[Category]:
        """Получение подкатегорий для указанной категории"""
        async with self._sf() as s:
            stmt = (
                select(Category)
                .where(Category.parent_id == parent_id)
                #.order_by(Category.name)
            )
            res = await s.execute(stmt)
            return list(res.scalars())

    # name = name.strip()
    async def get_by_name_within_parent(self, *, name: str, parent_id: Optional[int]) -> Optional[Category]:
        """ Получение категории по имени
        — если parent_id=None: найти категорию по имени;
        — если parent_id=X: найти подкатегорию по имени внутри категории X.
        """
        async with self._sf() as s:
            cond = and_(
                Category.name == name,
                Category.parent_id.is_(None)
                if parent_id is None
                else Category.parent_id == parent_id,
            )
            res = await s.execute(select(Category).where(cond))
            return res.scalar_one_or_none()


    async def exists_by_name_within_parent(self, *, name: str, parent_id: Optional[int]) -> bool:
        """Проверка «есть ли такая запись?»  Когда нужен просто ответ «есть / нет»"""
        async with self._sf() as s:
            cond = and_(
                Category.name == name,
                Category.parent_id.is_(None)
                if parent_id is None
                else Category.parent_id == parent_id,
            )
            res = await s.execute(select(exists().where(cond)))
            return bool(res.scalar())

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    async def create(self, *, name: str, emoji: Optional[str] = None, parent_id: Optional[int] = None) -> Category:
        """
        — parent_id=None: создать категорию;
        — parent_id=X: создать подкатегорию в категории X.
        (Дубликаты по (parent_id, name) не создаст — вернёт существующую.)
        """
        name = name.strip()
        obj = Category(name=name, emoji=emoji, parent_id=parent_id)
        async with self._sf() as s:
            s.add(obj)
            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            await s.refresh(obj)
            return obj

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

            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            await s.refresh(obj)
            return obj

    async def delete(self, category_id: int) -> bool:
        """Удалить категорию или подкатегорию (Если удаляешь категорию — её подкатегории тоже уйдут, каскад)
        Возвращает True если удалили, False если не нашли/ошибка."""
        async with self._sf() as s:
            obj = await s.get(Category, category_id)
            if not obj:
                return False

            await s.delete(obj)
            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            return True