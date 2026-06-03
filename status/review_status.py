from enum import StrEnum

class ReviewStatus(StrEnum):
    """Статус модерации отзыва клиента.

    Отзыв сначала попадает на проверку, затем может быть опубликован,
    скрыт из публичного отображения или отклонён.
    """

    PENDING = "pending"      # отзыв создан клиентом и ожидает проверки менеджером/админом
    PUBLISHED = "published"  # отзыв прошёл проверку и может отображаться публично
    HIDDEN = "hidden"        # отзыв временно скрыт из публичного отображения
    REJECTED = "rejected"    # отзыв отклонён и не должен публиковаться


# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
ALLOWED_STATUS_TRANSITIONS: dict[ReviewStatus, frozenset[ReviewStatus]] = {
    ReviewStatus.PENDING: frozenset({ReviewStatus.PUBLISHED, ReviewStatus.REJECTED}),
    ReviewStatus.PUBLISHED: frozenset({ReviewStatus.HIDDEN}),
    ReviewStatus.HIDDEN: frozenset({ReviewStatus.PUBLISHED, ReviewStatus.REJECTED}),
    ReviewStatus.REJECTED: frozenset({ReviewStatus.PENDING}),
}