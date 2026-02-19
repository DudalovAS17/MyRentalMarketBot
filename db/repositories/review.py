from __future__ import annotations

from typing import Optional, List, Callable
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.review import Review

class ReviewRepository:
    """Репозиторий для работы с отзывами"""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sf = session_factory

    async def get_by_id(self, review_id: int) -> Optional[Review]:
        """Получение отзыва по ID"""
        async with self._sf() as s:
            return await s.get(Review, review_id)

    async def list_by_rental_id(self, rental_id: int) -> List[Review]:
        """Получение отзывов по ID аренды"""
        async with self._sf() as s:
            stmt = (
                select(Review)
                .where(Review.rental_id == rental_id)
                .order_by(Review.created_at.asc())
            )

            res = await s.execute(stmt)
            return list(res.scalars())

    async def list_by_reviewer_id(self, reviewer_id: int) -> List[Review]:
        """Получение отзывов по ID автора"""
        async with self._sf() as s:
            stmt = (
                select(Review)
                .where(Review.reviewer_id == reviewer_id)
                .order_by(Review.created_at.desc())
            )

            res = await s.execute(stmt)
            return list(res.scalars())

    async def list_by_reviewee_id(self, reviewee_id: int) -> List[Review]:
        """Получение отзывов по ID получателя"""
        async with self._sf() as s:
            stmt = (
                select(Review)
                .where(Review.reviewee_id == reviewee_id)
                .order_by(Review.created_at.desc())
            )

            res = await s.execute(stmt)
            return list(res.scalars())

    async def exists_for_rental(self, *, rental_id: int, reviewer_id: int) -> bool:
        """Проверка: оставлял ли пользователь отзыв по сделке"""
        async with self._sf() as s:
            stmt = (
                select(Review.id)
                .where(Review.rental_id == rental_id, Review.reviewer_id == reviewer_id)
                #.limit(1)
            )

            res = await s.execute(stmt)
            return res.scalar_one_or_none() is not None

    async def create(self, *, rental_id: int, reviewer_id: int, reviewee_id: int, rating: int, comment: str | None) -> Review:
        """Создание нового отзыва"""
        review = Review(
            rental_id=rental_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            rating=rating,
            comment=comment,
        )
        async with self._sf() as s:
            s.add(review)

            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise

            await s.refresh(review)
            return review

    # 🔹 Почему нет update() - Мы заранее договорились: отзыв — финальный артефакт
    # 🔹 delete - тоже убираем, т.к. если пользователь удалит отзыв, то это на рейтинг повлияет задним числом


    # вставил без осознания
    async def get_stats_for_user(self, *, reviewee_id: int) -> tuple[float, int]:
        """Вернуть (avg_rating, count) по пользователю. avg_rating=0.0 если отзывов нет."""
        async with self._sf() as s:
            stmt = select(
                func.coalesce(func.avg(Review.rating), 0.0),
                func.count(Review.id),
            ).where(Review.reviewee_id == reviewee_id)

            avg_rating, count = (await s.execute(stmt)).one()
            return float(avg_rating), int(count)