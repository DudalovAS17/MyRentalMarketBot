import logging
from typing import Optional

from db.repositories.review import ReviewRepository
from db.repositories.rental import RentalRepository

from schemas.review import ReviewCreate, ReviewOut, ReviewCreateInternal
from status.rental_status import RentalStatus
from utils.errors import NotFoundError, ConflictError, ForbiddenError

logger = logging.getLogger(__name__)

class ReviewService:
    """Бизнес-логика работы с отзывами"""

    def __init__(self, repo: ReviewRepository, rental_repo: RentalRepository):
        self.repo = repo
        self.rental_repo = rental_repo

    # ────────────────────────────────────────── DTO helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _to_out(review) -> ReviewOut:
        return ReviewOut.model_validate(review)

    @classmethod
    def _to_out_list(cls, reviews) -> list[ReviewOut]:
        return [cls._to_out(review) for review in reviews]

    # ─────────────────────────────────────── Business validation ─────────────────────────────────────────────────────
    @staticmethod
    def _ensure_rental_completed(status: RentalStatus) -> None:
        if status != RentalStatus.COMPLETED:
            raise ConflictError("Отзыв можно оставить только после завершения аренды")

    @staticmethod
    def _ensure_actor_is_rental_user(*, rental_user_id: int, actor_id: int) -> None:
        if actor_id != rental_user_id:
            raise ForbiddenError("Нет доступа: отзыв может оставить только клиент этой заявки")

    async def _ensure_review_not_exists(self, *, rental_id: int, user_id: int) -> None:
        already_exists = await self.repo.exists_for_rental(rental_id=rental_id, user_id=user_id)
        if already_exists:
            raise ConflictError("Вы уже оставили отзыв по этой заявке")

    # ────────────────────────────────────────── Read methods ──────────────────────────────────────────────────────────
    async def get_by_id(self, review_id: int, *, strict: bool = False) -> Optional[ReviewOut]:
        """Получить отзыв по его ID."""
        review = await self.repo.get_by_id(review_id)
        if not review:
            if strict:
                raise NotFoundError(f"Отзыв не найден: id={review_id}")
            return None

        return self._to_out(review)

    async def list_reviews_by_rental(self, rental_id: int) -> list[ReviewOut]:
        """Возвращает все отзывы, связанные с конкретной заявкой"""
        reviews = await self.repo.list_by_rental_id(rental_id)
        return self._to_out_list(reviews)

    async def list_reviews_by_user(self, user_id: int) -> list[ReviewOut]:
        """Вернуть отзывы, оставленные клиентом."""
        reviews = await self.repo.list_by_user_id(user_id)
        return self._to_out_list(reviews)

    async def list_reviews_by_item(self, item_id: int, *, published_only: bool = True) -> list[ReviewOut]:
        """Вернуть отзывы по товару каталога."""
        reviews = await self.repo.list_by_item_id(item_id, published_only=published_only)
        return self._to_out_list(reviews)

    # ─────────────────────────────────────────── write methods ────────────────────────────────────────────────────────
    async def create_review(self, actor_id: int, data: ReviewCreate) -> Optional[ReviewOut]:
        """Создать отзыв клиента по завершённой заявке на аренду."""
        rental = await self.rental_repo.get_by_id(data.rental_id)
        if not rental:
            raise NotFoundError(f"Заявка не найдена: id={data.rental_id}")

        # Проверки
        self._ensure_rental_completed(rental.status)
        self._ensure_actor_is_rental_user(rental_user_id=rental.user_id, actor_id=actor_id)
        await self._ensure_review_not_exists(rental_id=data.rental_id, user_id=actor_id)

        # Создаём отзыв
        review_data = ReviewCreateInternal(
            rental_id=data.rental_id,
            item_id=rental.item_id,
            user_id=actor_id,
            rating=data.rating,
            comment=data.comment,
        )
        review = await self.repo.create(review_data)

        logger.info("Отзыв создан: id=%s rental_id=%s item_id=%s user_id=%s rating=%s",
            review.id, review.rental_id, review.item_id, review.user_id, review.rating)
        # Убрал - Пересчитываем рейтинг пользователя
        return self._to_out(review)


    # Удалил: recalculate_user_rating - Пересчитать рейтинг пользователя на основе всех отзывов