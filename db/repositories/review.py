from sqlalchemy import select, func
from decimal import Decimal
from typing import Optional

from db.models.review import Review
from db.repositories.base import BaseRepository

from schemas.review import ReviewAdminUpdate, ReviewCreateInternal, ReviewUpdate
from status.review_status import ReviewStatus

class ReviewRepository(BaseRepository):
    """Репозиторий отзывов клиентов о товарах, заявках и сервисе компании."""

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _apply_recent_order(stmt):
        """Стабильный порядок выдачи отзывов: новые сначала."""
        return stmt.order_by(Review.created_at.desc(), Review.id.desc())

    @staticmethod
    def _apply_pagination(stmt, *, limit: Optional[int], offset: int):
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        return stmt

    @staticmethod
    def _apply_rental_filter(stmt, rental_id: int):
        """Оставить только отзывы по указанной заявке."""
        return stmt.where(Review.rental_id == rental_id)

    @staticmethod
    def _apply_user_filter(stmt, user_id: int):
        """Оставить только отзывы указанного клиента."""
        return stmt.where(Review.user_id == user_id)

    @staticmethod
    def _apply_item_filter(stmt, item_id: int):
        """Оставить только отзывы по указанному товару каталога."""
        return stmt.where(Review.item_id == item_id)

    @staticmethod
    def _apply_status_filter(stmt, status: ReviewStatus):
        """Оставить только отзывы с указанным статусом модерации."""
        return stmt.where(Review.status == status)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def get_by_id(self, review_id: int) -> Optional[Review]:
        """Получить отзыв по ID."""
        async with self._session() as s:
            return await s.get(Review, review_id)

    async def list_all(self, *, limit: Optional[int] = None, offset: int = 0) -> list[Review]:
        """Вернуть отзывы клиентов."""
        async with self._session() as s:
            stmt = select(Review)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            return await self._list(s, stmt)

    async def list_by_rental_id(self, rental_id: int,
                                *, limit: Optional[int] = None, offset: int = 0) -> list[Review]:
        """Вернуть отзывы по заявке на аренду."""
        async with self._session() as s:
            stmt = select(Review)
            stmt = self._apply_rental_filter(stmt, rental_id)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            return await self._list(s, stmt)

    async def list_by_user_id(self, user_id: int,
                              *, limit: Optional[int] = None, offset: int = 0) -> list[Review]:
        """Вернуть отзывы, оставленные клиентом."""
        async with self._session() as s:
            stmt = select(Review)
            stmt = self._apply_user_filter(stmt, user_id)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            return await self._list(s, stmt)

    async def list_by_item_id(self, item_id: int,
        *, published_only: bool = False, limit: Optional[int] = None, offset: int = 0) -> list[Review]:
        """Вернуть отзывы по товару каталога."""
        async with self._session() as s:
            stmt = select(Review)
            stmt = self._apply_item_filter(stmt, item_id)
            if published_only:
                stmt = self._apply_status_filter(stmt, ReviewStatus.PUBLISHED)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            return await self._list(s, stmt)

    async def list_by_status(self, status: ReviewStatus,
                             *, limit: Optional[int] = None, offset: int = 0) -> list[Review]:
        """Вернуть отзывы с указанным статусом модерации."""
        async with self._session() as s:
            stmt = select(Review)
            stmt = self._apply_status_filter(stmt, status)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            return await self._list(s, stmt)

    async def exists_for_rental(self, *, rental_id: int, user_id: int) -> bool:
        """Проверить, оставлял ли клиент отзыв по указанной заявке."""
        async with self._session() as s:
            stmt = select(Review.id)
            stmt = self._apply_rental_filter(stmt, rental_id)
            stmt = self._apply_user_filter(stmt, user_id)
            stmt = stmt.limit(1)
            return (await self._one_or_none(s, stmt)) is not None
            # return res.scalar_one_or_none() is not None

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def create(self, review_data: ReviewCreateInternal) -> Review:
        """Создать отзыв клиента."""
        async with self._session() as s:
            review = Review(**review_data.model_dump())
            return await self._add_commit_refresh(s, review)

    async def update(self, review_id: int, update_data: ReviewUpdate) -> Optional[Review]:
        """Обновить оценку или текст отзыва клиента."""
        async with self._session() as s:
            review: Optional[Review] = await s.get(Review, review_id)
            if not review:
                return None

            data = update_data.model_dump(exclude_unset=True)
            if not data:
                return review

            changed = False
            for field_name, value in data.items():
                if getattr(review, field_name) != value:
                    setattr(review, field_name, value)
                    changed = True

            if not changed:
                return review

            return await self._commit_refresh(s, review)

    async def delete(self, review_id: int) -> bool:
        """Удалить отзыв."""
        async with self._session() as s:
            review = await s.get(Review, review_id)
            if not review:
                return False

            return await self._delete_commit(s, review)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def admin_update(self, review_id: int, update_data: ReviewAdminUpdate) -> Optional[Review]:
        """Обновить статус модерации или внутреннюю заметку администратора."""
        async with self._session() as s:
            review: Optional[Review] = await s.get(Review, review_id)
            if not review:
                return None

            data = update_data.model_dump(exclude_unset=True)
            if not data:
                return review

            changed = False
            for field_name, value in data.items():
                if getattr(review, field_name) != value:
                    setattr(review, field_name, value)
                    changed = True

            if not changed:
                return review

            return await self._commit_refresh(s, review)

    async def set_status(self, review_id: int, status: ReviewStatus, *, admin_note: Optional[str] = None) -> Optional[Review]:
        """Установить статус модерации отзыва."""
        update_data = ReviewAdminUpdate(status=status)
        if admin_note is not None:
            update_data.admin_note = admin_note

        return await self.admin_update(review_id, update_data)

    async def get_stats_for_item(self,
                            *, item_id: int, status: Optional[ReviewStatus] = ReviewStatus.PUBLISHED) -> tuple[Decimal, int]:
        """Вернуть (avg_rating, count) по товару каталога."""
        async with self._session() as s:
            stmt = select(
                func.coalesce(func.avg(Review.rating), Decimal("0.00")),
                func.count(Review.id),
            )
            stmt = self._apply_item_filter(stmt, item_id)
            if status is not None:
                stmt = self._apply_status_filter(stmt, status)

            avg_rating, count = (await s.execute(stmt)).one()
            return Decimal(avg_rating), int(count)