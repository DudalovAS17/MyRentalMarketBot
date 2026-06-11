from typing import Optional
from sqlalchemy import select, exists, and_

from db.models.category import Category
from db.repositories.base import BaseRepository

"""
_UNSET = object() для update (убрал update пока)
Причина: позволяет отличать: "поле не передали", от "поле передали как None".
Это особенно важно для nullable-полей: emoji/parent_id/slug


_slug_within_parent_condition: slug
отдельный поиск по slug внутри родителя.


list_roots с active_only=True:
Причина: для клиентского каталога по умолчанию логично показывать только активные категории.
А если админке нужны все.


Сортировка стала правильной:
.order_by(Category.sort_order.asc(), Category.name.asc(), Category.id.asc())
Причина: sort_order теперь главный порядок каталога, а name/id — стабильные tie-breakers.


"""

"""Построить условие поиска категории по имени внутри конкретного родителя.

Используется для проверки уникальности и поиска категории/подкатегории:
- если parent_id is None — ищем корневую категорию с таким name;
- если parent_id задан — ищем подкатегорию с таким name внутри указанной категории.

Не выполняет запрос к БД, а только возвращает SQLAlchemy-условие для where().
"""

"""Построить условие поиска категории по slug внутри конкретного родителя.

Используется для поиска и проверки уникальности машинного имени категории:
- если parent_id is None — ищем корневую категорию с таким slug;
- если parent_id задан — ищем подкатегорию с таким slug внутри указанной категории.

Slug нужен для seed-данных, callback/deeplink-навигации и стабильных технических ссылок.
Не выполняет запрос к БД, а только возвращает SQLAlchemy-условие для where().
"""

class CategoryRepository(BaseRepository):
    """Репозиторий категорий и подкатегорий каталога."""

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _name_within_parent_condition(name: str, parent_id: Optional[int]):
        """Построить условие поиска категории по имени внутри конкретного родителя."""
        return and_(
            Category.name == name,
            Category.parent_id.is_(None)
            if parent_id is None
            else Category.parent_id == parent_id,
        )

    @staticmethod
    def _slug_within_parent_condition(slug: str, parent_id: Optional[int]):
        """Построить условие поиска категории по slug внутри конкретного родителя."""
        return and_(
            Category.slug == slug,
            Category.parent_id.is_(None)
            if parent_id is None
            else Category.parent_id == parent_id,
        )

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def list_all(self, *, active_only: bool = False) -> list[Category]:
        """Получить все категории и подкатегории.

        По умолчанию возвращает все записи, включая скрытые категории,
        что удобно для админки. Для публичного каталога можно передать active_only=True."""
        async with self._session() as s:
            stmt = select(Category)
            if active_only:
                stmt = stmt.where(Category.is_active.is_(True))

            stmt = stmt.order_by(Category.sort_order.asc(), Category.name.asc(), Category.id.asc())
            return await self._list(s, stmt)

    async def list_roots(self, *, active_only: bool = True) -> list[Category]:
        """Достает все активные категории без подкатегорий в порядке каталога"""
        async with self._session() as s:
            stmt = select(Category).where(Category.parent_id.is_(None))
            if active_only:
                stmt = stmt.where(Category.is_active.is_(True))

            stmt = stmt.order_by(Category.sort_order.asc(), Category.name.asc(), Category.id.asc())
            return await self._list(s, stmt)

    async def get_by_id(self, category_id: int) -> Optional[Category]:
        """Получение категории и подкатегории по ID"""
        async with self._session() as s:
            return await s.get(Category, category_id)

    async def list_subcategories(self, parent_id: int, *, active_only: bool = True) -> list[Category]:
        """Получение активных подкатегорий для указанной категории в порядке каталога"""
        async with self._session() as s:
            stmt = select(Category).where(Category.parent_id == parent_id)
            if active_only:
                stmt = stmt.where(Category.is_active.is_(True))

            stmt = stmt.order_by(Category.sort_order.asc(), Category.name.asc(), Category.id.asc())
            return await self._list(s, stmt)

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

    async def get_by_slug_within_parent(self, *, slug: str, parent_id: Optional[int]) -> Optional[Category]:
        """Получение категории или подкатегории по slug внутри родителя."""
        async with self._session() as s:
            cond = self._slug_within_parent_condition(slug, parent_id)
            return await self._one_or_none(s, select(Category).where(cond))

    async def exists_by_slug_within_parent(self, *, slug: str, parent_id: Optional[int]) -> bool:
        """Проверка существования категории или подкатегории по slug внутри родителя."""
        async with self._session() as s:
            cond = self._slug_within_parent_condition(slug, parent_id)
            return await self._exists(s, select(exists().where(cond)))

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def create(
            self,
            *,
            name: str,
            emoji: Optional[str] = None,
            parent_id: Optional[int] = None,
            sort_order: int = 0,
            is_active: bool = True,
            slug: Optional[str] = None,
    ) -> Category:
        """
        Создать категорию или подкатегорию.

        — parent_id=None: создать категорию
        — parent_id=X: создать подкатегорию в категории X
        """
        async with self._session() as s:
            obj = Category(
                name=name,
                emoji=emoji,
                parent_id=parent_id,
                sort_order=sort_order,
                is_active=is_active,
                slug=slug,
            )
            return await self._add_commit_refresh(s, obj)

    async def delete(self, category_id: int) -> bool:
        """Удалить категорию или подкатегорию (Если удаляешь категорию — её подкатегории тоже уйдут, каскад)
        Возвращает True если удалили, False если не нашли/ошибка"""
        async with self._session() as s:
            obj = await s.get(Category, category_id)
            if not obj:
                return False

            return await self._delete_commit(s, obj)