"""
backend/models/submission.py

SQLAlchemy ORM model for the Submission table.
"""

from sqlalchemy import VARCHAR, CHAR, DateTime, Enum, ForeignKey, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Submission(Base):
    __tablename__ = "Submission"

    submission_id: Mapped[str] = mapped_column(VARCHAR(30), primary_key=True)
    learner_id: Mapped[str] = mapped_column(
        VARCHAR(20), ForeignKey("Learner.learner_id"), nullable=False
    )
    assessment_id: Mapped[str] = mapped_column(
        VARCHAR(20), ForeignKey("Assessment.assessment_id"), nullable=False
    )
    attempt_no: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1", nullable=False)
    submitted_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    content_reference: Mapped[str | None] = mapped_column(VARCHAR(255), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("SUBMITTED", "LATE", "WITHDRAWN", name="submission_status_enum"),
        default="SUBMITTED",
        server_default="SUBMITTED",
        nullable=False,
    )

    # Relationships
    learner: Mapped["Learner"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Learner", back_populates="submissions"
    )
    assessment: Mapped["Assessment"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Assessment", back_populates="submissions"
    )
    report: Mapped["SimilarityReport | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "SimilarityReport", back_populates="submission", uselist=False
    )
