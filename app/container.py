from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings

from db.repositories.user import UserRepository
from db.repositories.category import CategoryRepository
from db.repositories.item import ItemRepository
from db.repositories.rental import RentalRepository
from db.repositories.photo import PhotoRepository
from db.repositories.admin import AdminActionRepository
from db.repositories.review import ReviewRepository
from db.repositories.support_ticket import SupportTicketRepository

from services.user_service import UserService
from services.category_service import CategoryService
from services.item_service import ItemService
from services.rental_service import RentalService
from services.photo_service import PhotoService
from services.review_service import ReviewService
from services.admin_service import AdminActionService
from services.admin_rental_service import AdminRentalService
from services.support_service import SupportService
from services.notif_service import NotificationService


@dataclass(frozen=True, slots=True)
class AppServices:
    user_service: UserService
    category_service: CategoryService
    item_service: ItemService
    rental_service: RentalService
    photo_service: PhotoService
    review_service: ReviewService
    admin_service: AdminActionService
    admin_rental_service: AdminRentalService
    support_service: SupportService
    notification_service: NotificationService

def build_services(
    *,
    bot: Bot,
    session_factory: Callable[[], AsyncSession],
) -> AppServices:
    # repositories
    user_repo = UserRepository(session_factory)
    item_repo = ItemRepository(session_factory)
    rental_repo = RentalRepository(session_factory)
    category_repo = CategoryRepository(session_factory)
    photo_repo = PhotoRepository(session_factory)
    review_repo = ReviewRepository(session_factory)
    admin_repo = AdminActionRepository(session_factory)
    support_repo = SupportTicketRepository(session_factory)

    # services (domain layer)
    user_service = UserService(user_repo, frozenset(settings.admin_ids))
    rental_service = RentalService(rental_repo)  # , item_service, user_service, notification_service
    item_service = ItemService(item_repo, rental_service)
    notification_service = NotificationService(bot)
    category_service = CategoryService(category_repo)
    photo_service = PhotoService(photo_repo)
    review_service = ReviewService(review_repo, rental_repo, user_repo)
    admin_service = AdminActionService(admin_repo)
    admin_rental_service = AdminRentalService(rental_repo, admin_service) # item_service, user_service,
    support_service = SupportService(support_repo)

    return AppServices(
        user_service=user_service,
        category_service=category_service,
        item_service=item_service,
        rental_service=rental_service,
        photo_service=photo_service,
        review_service=review_service,
        admin_service=admin_service,
        admin_rental_service=admin_rental_service,
        support_service=support_service,
        notification_service=notification_service,
    )