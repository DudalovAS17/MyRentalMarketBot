from __future__ import annotations

from typing import Optional
from sqlalchemy import select, func

from db.models.review import Review
from db.repositories.base import BaseRepository


class ReviewRepository(BaseRepository):
    """Репозиторий для работы с отзывами"""
    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    async def get_by_id(self, review_id: int) -> Optional[Review]:
        """Получение отзыва по ID"""
        async with self._session() as s:
            return await s.get(Review, review_id)

    async def list_by_rental_id(self, rental_id: int) -> list[Review]:
        """Получение отзывов по ID аренды"""
        async with self._session() as s:
            stmt = (
                select(Review)
                .where(Review.rental_id == rental_id)
                .order_by(Review.created_at.asc())
            )
            return await self._list(s, stmt)

    async def list_by_reviewer_id(self, reviewer_id: int) -> list[Review]:
        """Получение отзывов по ID автора"""
        async with self._session() as s:
            stmt = (
                select(Review)
                .where(Review.reviewer_id == reviewer_id)
                .order_by(Review.created_at.desc())
            )
            return await self._list(s, stmt)

    async def list_by_reviewee_id(self, reviewee_id: int) -> list[Review]:
        """Получение отзывов по ID получателя"""
        async with self._session() as s:
            stmt = (
                select(Review)
                .where(Review.reviewee_id == reviewee_id)
                .order_by(Review.created_at.desc())
            )
            return await self._list(s, stmt)

    async def exists_for_rental(self, *, rental_id: int, reviewer_id: int) -> bool:
        """Проверка: оставлял ли пользователь отзыв по сделке"""
        async with self._session() as s:
            stmt = (
                select(Review.id)
                .where(Review.rental_id == rental_id, Review.reviewer_id == reviewer_id)
                #.limit(1)
            )

            res = await s.execute(stmt)
            return res.scalar_one_or_none() is not None
            # return (await self._one_or_none(s, stmt)) is not None

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def create(self, *, rental_id: int, reviewer_id: int, reviewee_id: int, rating: int, comment: str | None) -> Review:
        """Создание нового отзыва"""
        review = Review(
            rental_id=rental_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            rating=rating,
            comment=comment,
        )
        async with self._session() as s:
            return await self._add_commit_refresh(s, review)

    # 🔹 Почему нет update() - Мы заранее договорились: отзыв — финальный артефакт
    # 🔹 delete - тоже убираем, т.к. если пользователь удалит отзыв, то это на рейтинг повлияет задним числом

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    # вставил без осознания
    async def get_stats_for_user(self, *, reviewee_id: int) -> tuple[float, int]:
        """Вернуть (avg_rating, count) по пользователю. avg_rating=0.0 если отзывов нет."""
        async with self._session() as s:
            stmt = select(
                func.coalesce(func.avg(Review.rating), 0.0),
                func.count(Review.id),
            ).where(Review.reviewee_id == reviewee_id)

            avg_rating, count = (await s.execute(stmt)).one()
            return float(avg_rating), int(count)