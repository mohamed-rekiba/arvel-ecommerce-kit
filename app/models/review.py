"""The Review model — customer feedback on a polymorphic subject (arvel morph relations)."""

from typing import Any, ClassVar

from arvel import Model

from app.enums import ReviewStatus


class Review(Model):
    __table_name__ = "reviews"
    __fields__: ClassVar[dict[str, type]] = {
        "subject_type": str,
        "subject_id": int,
        "user_id": int,
        "rating": int,
        "title": str,
        "body": str,
        "status": str,
    }
    __fillable__: ClassVar[list[str]] = [
        "subject_type",
        "subject_id",
        "user_id",
        "rating",
        "title",
        "body",
        "status",
    ]
    __casts__: ClassVar[dict[str, Any]] = {"status": ReviewStatus}

    def subject(self) -> Any:
        return self.morph_to("subject")

    def user(self) -> Any:
        from app.models.user import User

        return self.belongs_to(User)
