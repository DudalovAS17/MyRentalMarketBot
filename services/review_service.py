import logging
from typing import Optional

from db.repositories.review import ReviewRepository
from db.repositories.rental import RentalRepository
from db.repositories.user import UserRepository

from schemas.review import ReviewCreate, ReviewOut
from status.rental_status import RentalStatus
from utils.errors import NotFoundError, ConflictError

logger = logging.getLogger(__name__)

class ReviewService:
    """Бизнес-логика работы с отзывами"""

    def __init__(self, review_repo: ReviewRepository, rental_repo: RentalRepository, user_repo: UserRepository):
        self.review_repo = review_repo
        self.rental_repo = rental_repo
        self.user_repo = user_repo

    # ────────────────────────────────────────── Read methods ──────────────────────────────────────────────────────────
    async def get_by_id(self, review_id: int, *, strict: bool = False) -> Optional[ReviewOut]:
        """Получает один конкретный отзыв по его ID"""
        review = await self.review_repo.get_by_id(review_id)
        if not review:
            if strict:
                raise NotFoundError(f"Отзыв не найден: id={review_id}")
            return None

        return ReviewOut.model_validate(review)

    async def list_reviews_by_rental(self, rental_id: int) -> list[ReviewOut]:
        """Возвращает все отзывы, связанные с конкретной сделкой"""
        reviews = await self.review_repo.list_by_rental_id(rental_id)
        return [ReviewOut.model_validate(r) for r in reviews]

    async def list_reviews_about_user(self, user_id: int) -> list[ReviewOut]:
        """Отзывы о пользователе"""
        reviews = await self.review_repo.list_by_reviewee_id(user_id)
        return [ReviewOut.model_validate(r) for r in reviews]

    async def list_reviews_by_user(self, user_id: int) -> list[ReviewOut]:
        """Отзывы, оставленные пользователем"""
        reviews = await self.review_repo.list_by_reviewer_id(user_id)
        return [ReviewOut.model_validate(r) for r in reviews]

    # ─────────────────────────────────────────── write methods ────────────────────────────────────────────────────────
    async def create_review(self, actor_id: int, data: ReviewCreate, *, strict: bool = True,) -> Optional[ReviewOut]:
        """Создать отзыв"""

        rental = await self.rental_repo.get_by_id(data.rental_id)
        if not rental:
            if strict:
                raise NotFoundError(f"Сделка не найдена: id={data.rental_id}")
            return None

        if rental.status != RentalStatus.COMPLETED:
            raise ConflictError("Отзыв можно оставить только после завершения аренды")

        # actor должен быть участником сделки
        if actor_id not in (rental.renter_id, rental.owner_id):
            raise ConflictError("Нет доступа: вы не участник этой сделки")

        # Проверяем, что отзыв ещё не оставлен
        already_exists = await self.review_repo.exists_for_rental(
            rental_id=data.rental_id,
            reviewer_id=actor_id,
        )
        if already_exists:
            raise ConflictError("Вы уже оставили отзыв по этой сделке")

        # Кому оставляем отзыв (второй участник)
        reviewee_id = rental.owner_id if actor_id == rental.renter_id else rental.renter_id

        # Создаём отзыв
        comment = (data.comment.strip() if data.comment else None) or None
        review = await self.review_repo.create(
            rental_id=data.rental_id,
            reviewer_id=actor_id,
            reviewee_id=reviewee_id,
            rating=data.rating,
            comment=comment,
        )

        logger.info(
            "Review created id=%s rental_id=%s reviewer_id=%s reviewee_id=%s rating=%s",
            review.id, data.rental_id,  actor_id, reviewee_id, data.rating,
        )

        # Пересчитываем рейтинг пользователя
        await self.recalculate_user_rating(reviewee_id)

        return ReviewOut.model_validate(review)

    # ──────────────────────────────────── helper для create_review ────────────────────────────────────────────────────
    async def recalculate_user_rating(self, user_id: int) -> None:
        """Пересчитать рейтинг пользователя на основе всех отзывов"""
        avg_rating, count = await self.review_repo.get_stats_for_user(reviewee_id=user_id)

        await self.user_repo.update_rating(user_id=user_id, rating=avg_rating, rating_count=count)

        logger.info("Рейтинг пользователя %s обновлён: %s (%s отзывов)",user_id, avg_rating, count)