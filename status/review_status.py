from enum import StrEnum

class ReviewStatus(StrEnum):
    PENDING = "pending"
    PUBLISHED = "published"
    HIDDEN = "hidden"
    REJECTED = "rejected"
