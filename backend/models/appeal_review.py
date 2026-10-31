"""
backend/models/appeal_review.py

SQLAlchemy ORM model for the AppealReview table.
Independent reviewer's evaluation of an appeal.
Business rule: independence_verified must be TRUE before
the Appeal can be set to UPHELD or OVERTURNED.
"""

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Text, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class AppealReview(Base):
    __tablename__ = "AppealReview"

    review_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    appeal_id: Mapped[str] = mapped_column(
        VARCHAR(80), ForeignKey("Appeal.appeal_id"), nullable=False
    )
    reviewer_id: Mapped[str] = mapped_column(
        VARCHAR(20), ForeignKey("Reviewer.reviewer_id"), nullable=False
    )
    outcome: Mapped[str] = mapped_column(
        Enum("UPHELD", "OVERTURNED", "REMANDED", name="appeal_review_outcome_enum"),
        nullable=False,
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    independence_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    reviewed_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)

    # Relationships
    appeal: Mapped["Appeal"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Appeal", back_populates="reviews"
    )
    reviewer: Mapped["Reviewer"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Reviewer", back_populates="appeal_reviews"
    )
