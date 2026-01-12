from __future__ import annotations

import logging
from typing import Callable, Optional, List, Iterable

from sqlalchemy import select, exists, and_
from sqlalchemy.exc import IntegrityError

from sqlalchemy.ext.asyncio import AsyncSession

#from db.database import get_db_session
from db.models.category import Category

logger = logging.getLogger(__name__)


class CategoryRepository:
    """Синхронный репозиторий для Category.
    Создаёт и закрывает сессию в каждом методе
    DI: session_factory -> AsyncSession (новая сессия на каждый вызов)"""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sf = session_factory


    async def get_all(self) -> List[Category]:
        """Получает все категории (с подкатегориями)"""
        async with self._sf() as s:
            # stmt = select(Category)  # построили SQL запрос: дай все колонки из таблицы categories
            # result = await s.execute(stmt)  # отправили запрос в БД
                # list(result)[:2] даст [(<Category id=1>,), (<Category id=2>,), ...] - кортеж из одного элемента (ORM-объекта)
            # rows = result.scalars()  # убрали лишнюю обёртку-кортеж, Теперь это итератор.
                # Из результата вытаскиваем не кортежи колонок, а сами ORM-объекты Category
            # categories = list(rows)  # Материализуем итератор в список
                # categories -  [<Category id=1>, <Category id=2>, <Category id=3>]
            # return categories  # вернули
            res = await s.execute(select(Category))
            return list(res.scalars())

    """ То как раньше было
        @staticmethod
        def get_all() -> list[Category]:
            ""Получает все категории (с подкатегориями), как ORM-объекты""
            db: Session = get_db_session()
            if db is None:
                logger.error("Ошибка: Не удалось получить сессию БД")
                return []

            try:
                # return db.query(Category).filter(Category.parent_id == None).all() # без подкатегорий
                return db.query(Category).all() # c подкатегориями
            except Exception as e:
                logger.error("get_all() Ошибка при получении категорий: %s", e, exc_info=True)
                return []
            finally:
                db.close()
    """

    async def list_roots(self) -> List[Category]:
        """достает все категории, без подкатегорий. В алфав-м порядке"""
        async with self._sf() as s:
            stmt = (
                select(Category)
                .where(Category.parent_id.is_(None)) # parent_id = NULL
                .order_by(Category.name) # сортируем по имени, чтобы в UI было стабильно и красиво (алфавит)
            )
            res = await s.execute(stmt)
            return list(res.scalars())

    async def get_by_id(self, category_id: int) -> Optional[Category]:
        """Получение категории и подкатегории по ID"""
        async with self._sf() as s:
            return await s.get(Category, category_id)   # дай мне категорию с таким id
            # select(...).where(...) можно и так

    async def get_subcategories(self, parent_id: int) -> List[Category]:
        """Получение подкатегорий для указанной категории"""
        async with self._sf() as s:
            stmt = (
                select(Category)
                .where(Category.parent_id == parent_id)
                #.order_by(Category.name)
            )
            res = await s.execute(stmt)
            return list(res.scalars().all()) # без all()? !!!!!!!!!!!!!!!!!!!!!

    async def get_by_name_within_parent(self, *, name: str, parent_id: Optional[int]) -> Optional[Category]:
        """ Получение категории по имени
        — если parent_id=None: найти категорию по имени;
        — если parent_id=X: найти подкатегорию по имени внутри категории X.
        """
        name = name.strip() # убираем пробелы по краям
        async with self._sf() as s:
            cond = and_(
                Category.name == name, # точное совпадение имени
                Category.parent_id.is_(None)
                if parent_id is None # ищем среди категорий
                else Category.parent_id == parent_id, # иначе → ищем среди подкатегорий внутри указанной категории
            )
            res = await s.execute(select(Category).where(cond))
            return res.scalar_one_or_none()
            # select(Category).where(cond) - выбрать строки из таблицы categories, где выполняется условие cond
            # scalar_one_or_none() - вернёт объект Category, если нашли ровно одну строку, вернёт None, если не нашли

    async def exists_by_name_within_parent(self, *, name: str, parent_id: Optional[int]) -> bool:
        """Проверка «есть ли такая запись?»  Когда нужен просто ответ «есть / нет»"""
        name = name.strip()
        async with self._sf() as s:
            cond = and_(
                Category.name == name,
                Category.parent_id.is_(None)
                if parent_id is None
                else Category.parent_id == parent_id,
            )
            res = await s.execute(select(exists().where(cond)))
            return bool(res.scalar())

    # ── Write ────────────────────────────────────────────────────────────────

    async def create(self, *, name: str, emoji: Optional[str] = None, parent_id: Optional[int] = None) -> Category:
        """
        — parent_id=None: создать категорию;
        — parent_id=X: создать подкатегорию в категории X.
        (Дубликаты по (parent_id, name) не создаст — вернёт существующую.)
        """
        name = name.strip()
        obj = Category(name=name, emoji=emoji, parent_id=parent_id) # name=name.strip()
        async with self._sf() as s:
            s.add(obj) # планируем INSERT
            try:
                await s.commit() # Пытаемся записать
            except IntegrityError as e:
                await s.rollback()
                # дубликат по (parent_id, name) — вернём существующую
                cond = and_(
                    Category.name == name,
                    Category.parent_id.is_(None)
                    if parent_id is None
                    else Category.parent_id == parent_id,
                )
                res = await s.execute(select(Category).where(cond)) # Получение категории по имени (get_by_name_within_parent)
                existing = res.scalar_one_or_none()
                if existing:
                    logger.warning(
                        "category duplicate → return existing (parent_id=%s, name=%r, id=%s)",
                        parent_id, name, existing.id,
                    )
                    return existing
                logger.error(
                    "category create failed (parent_id=%s, name=%r): %s",
                    parent_id, name, e, exc_info=True
                )
                raise
            await s.refresh(obj)
            logger.info("category created id=%s name=%r parent_id=%s", obj.id, obj.name, obj.parent_id)
            return obj

    async def update(self, category_id: int, *, name: Optional[str] = None, emoji: Optional[str] = None) -> Optional[Category]:
        """переименовать/сменить emoji у категории или подкатегории."""
        async with self._sf() as s:
            obj = await s.get(Category, category_id)
            if not obj:
                logger.info("category not found for update (id=%s)", category_id)
                return None

            changed = False
            if isinstance(name, str):  # если это строка,
                new_name = name.strip()
                if new_name and new_name != obj.name: # и если она не пустая, и отличается от текущей
                    obj.name = new_name
                    changed = True
            if emoji is not None and emoji != obj.emoji:
                obj.emoji = emoji
                changed = True

            if not changed:
                return obj

            try:
                await s.commit()
            except IntegrityError as e:
                await s.rollback()
                logger.warning(
                    "category update conflict (id=%s, new_name=%r): %s",
                    category_id, name, e
                )
                return None
            await s.refresh(obj)
            logger.info("category updated id=%s", obj.id)
            return obj

    async def delete(self, category_id: int) -> int:
        """Удалить категорию или подкатегорию (Если удаляешь категорию — её подкатегории тоже уйдут, каскад)
        Возвращает 1 если удалили, 0 если не нашли/ошибка."""
        async with self._sf() as s:
            obj = s.get(Category, category_id)
            if not obj:
                logger.info("category not found for delete (id=%s)", category_id)
                return 0
            await s.delete(obj)
            try:
                await s.commit()
            except IntegrityError as e:
                await s.rollback()
                logger.error("category delete failed (id=%s): %s", category_id, e, exc_info=True)
                return 0
            logger.info("category deleted id=%s", category_id)
            return 1

""" мб не понадобится
    def initialize_defaults(self, defaults: Iterable[dict]) -> None:
        "" закинуть стартовый набор: список категорий с их подкатегориями
        defaults формат:
        [
          {"name": "Техника", "emoji": "🔧", "subcategories": ["Ноутбуки", "Смартфоны"]},
          ...
        ]
        Идемпотентно: дубликаты по (parent_id, name) не плодим.
        ""
        with self._sf() as s:
            for cat in defaults:
                root = self.create_root(name=cat["name"], emoji=cat.get("emoji"))
                for sub in cat.get("subcategories", []):
                    self.create_child(parent_id=root.id, name=sub)
"""