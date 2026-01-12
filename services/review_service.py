import logging
from typing import List, Optional

from db.models.review import Review
from db.models.rental import RentalStatus

from db.repositories.review import ReviewRepository
from db.repositories.rental import RentalRepository
from db.repositories.user import UserRepository

from schemas.review import ReviewCreate, ReviewOut #, ReviewUpdate

logger = logging.getLogger(__name__)


class ReviewService:
    """Бизнес-логика работы с отзывами"""
    def __init__(
        self,
        review_repo: ReviewRepository,
        rental_repo: RentalRepository,
        user_repo: UserRepository,
    ):
        self.review_repo = review_repo
        self.rental_repo = rental_repo
        self.user_repo = user_repo

    async def get_by_id(self, review_id: int) -> Optional[ReviewOut]:
        """Получает один конкретный отзыв по его ID"""
        review = await self.review_repo.get_by_id(review_id)
        if not review:
            return None
        return ReviewOut.model_validate(review)

    async def get_reviews_by_rental(self, rental_id: int) -> List[ReviewOut]:
        """Возвращает все отзывы, связанные с конкретной сделкой"""
        reviews = await self.review_repo.get_by_rental_id(rental_id)
        return [ReviewOut.model_validate(r) for r in reviews]

    async def get_reviews_about_user(self, user_id: int) -> List[ReviewOut]:
        """Отзывы о пользователе"""
        reviews = await self.review_repo.get_by_reviewee_id(user_id)
        return [ReviewOut.model_validate(r) for r in reviews]

    async def get_reviews_by_user(self, user_id: int) -> List[ReviewOut]:
        """Отзывы, оставленные пользователем"""
        reviews = await self.review_repo.get_by_reviewer_id(user_id)
        return [ReviewOut.model_validate(r) for r in reviews]

    async def create_review(self, data: ReviewCreate) -> ReviewOut:
        """
        Создать отзыв:
        - только по завершённой сделке
        - только участником сделки
        - только один отзыв на сделку
        (автоматически пересчитывает рейтинг получателя)
        """

        # 1️⃣ Проверяем сделку
        rental = await self.rental_repo.get_by_id(data.rental_id)
        if not rental:
            raise ValueError("Сделка не найдена")

        if rental.status != RentalStatus.COMPLETED:
            raise ValueError("Отзыв можно оставить только после завершения аренды")

        # 2️⃣ Проверяем участие пользователя
        if data.reviewer_id not in (rental.renter_id, rental.owner_id):
            raise PermissionError("Вы не участник этой сделки")

        # 3️⃣ Проверяем, что отзыв ещё не оставлен
        already_exists = await self.review_repo.exists_for_rental(
            rental_id=data.rental_id,
            reviewer_id=data.reviewer_id,
        )
        if already_exists:
            raise ValueError("Вы уже оставили отзыв по этой сделке")

        """
        # Определяем, кто оставляет отзыв (и о ком)
        expected_reviewee = (
            rental.owner_id
            if data.reviewer_id == rental.renter_id
            else rental.renter_id
        )
        """

        # 4️⃣ Валидируем рейтинг
        if not 1 <= data.rating <= 5:
            raise ValueError("Рейтинг должен быть от 1 до 5")

        # 5️⃣ Создаём отзыв
        review = await self.review_repo.create(
            rental_id=data.rental_id,
            reviewer_id=data.reviewer_id,
            reviewee_id=data.reviewee_id,
            rating=data.rating,
            comment=data.comment,
        )

        logger.info(
            "Создан отзыв: rental_id={}, reviewer_id={}, rating={}",
            data.rental_id,
            data.reviewer_id,
            data.rating,
        )

        # 6️⃣ Пересчитываем рейтинг пользователя
        await self.recalculate_user_rating(data.reviewee_id)

        return ReviewOut.model_validate(review)

    async def recalculate_user_rating(self, user_id: int) -> None:
        """Пересчитать рейтинг пользователя на основе всех отзывов"""

        reviews: List[Review] = await self.review_repo.get_by_reviewee_id(user_id)

        if not reviews:
            await self.user_repo.update_rating(
                user_id=user_id,
                rating=0.0,
                rating_count=0,
            )
            return

        # reviews = [Review(rating=5), Review(rating=4), Review(rating=3),]
        total_rating = sum(r.rating for r in reviews) # total = 5 + 4 + 3 = 12
        count = len(reviews) # count = 3 - количество отзывов
        avg_rating = round(total_rating / count, 1) #  average = 12 / 3 = 4.0 - средний рейтинг пользователя
        # round(4.3333, 1) → 4.3 - округляет

        await self.user_repo.update_rating(
            user_id=user_id,
            rating=avg_rating,
            rating_count=count,
        )

        logger.info(
            "Рейтинг пользователя {} обновлён: {} ({} отзывов)",
            user_id,
            avg_rating,
            count,
        )