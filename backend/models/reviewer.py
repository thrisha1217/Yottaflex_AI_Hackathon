"""
backend/models/reviewer.py

SQLAlchemy ORM model for the Reviewer table.
"""

from sqlalchemy import VARCHAR, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Reviewer(Base):
    __tablename__ = "Reviewer"

    reviewer_id: Mapped[str] = mapped_column(VARCHAR(20), primary_key=True)
    full_name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    email: Mapped[str] = mapped_column(VARCHAR(150), unique=True, nullable=False)
    reviewer_role: Mapped[str] = mapped_column(
        Enum("INSTRUCTOR", "ACADEMIC_ADMIN", "REVIEWER", name="reviewer_role_enum"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum("ACTIVE", "INACTIVE", name="reviewer_status_enum"),
        default="ACTIVE",
        server_default="ACTIVE",
        nullable=False,
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)

    # Relationships
    case_assignments: Mapped[list["CaseReviewer"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "CaseReviewer", back_populates="reviewer"
    )
    decisions: Mapped[list["Decision"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Decision", back_populates="reviewer"
    )
    appeal_reviews: Mapped[list["AppealReview"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "AppealReview", back_populates="reviewer"
    )
