"""
backend/models/appeal.py

SQLAlchemy ORM model for the Appeal table.
Represents a student's formal challenge to an investigation decision.
"""

from sqlalchemy import DateTime, Enum, ForeignKey, SmallInteger, Text, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Appeal(Base):
    __tablename__ = "Appeal"

    appeal_id: Mapped[str] = mapped_column(VARCHAR(80), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        VARCHAR(30), ForeignKey("IntegrityCase.case_id"), nullable=False
    )
    learner_id: Mapped[str] = mapped_column(
        VARCHAR(20), ForeignKey("Learner.learner_id"), nullable=False
    )
    appeal_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    appeal_status: Mapped[str] = mapped_column(
        Enum(
            "SUBMITTED",
            "UNDER_REVIEW",
            "UPHELD",
            "OVERTURNED",
            "REMANDED",
            name="appeal_status_enum",
        ),
        default="SUBMITTED",
        server_default="SUBMITTED",
        nullable=False,
    )
    resolved_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    case: Mapped["IntegrityCase"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "IntegrityCase", back_populates="appeals"
    )
    reviews: Mapped[list["AppealReview"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "AppealReview", back_populates="appeal"
    )
