"""
backend/models/similarity_report.py

SQLAlchemy ORM model for the SimilarityReport table.
"""

from sqlalchemy import VARCHAR, Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class SimilarityReport(Base):
    __tablename__ = "SimilarityReport"

    report_id: Mapped[str] = mapped_column(VARCHAR(80), primary_key=True)
    submission_id: Mapped[str] = mapped_column(
        VARCHAR(30), ForeignKey("Submission.submission_id"), nullable=False
    )
    rule_id: Mapped[str | None] = mapped_column(
        VARCHAR(20), ForeignKey("IntegrityRule.rule_id"), nullable=True
    )
    report_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    similarity_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    matched_source_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    review_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    report_status: Mapped[str] = mapped_column(
        Enum(
            "GENERATED",
            "REVIEW_REQUIRED",
            "MONITOR",
            "NO_REVIEW",
            name="report_status_enum",
        ),
        nullable=False,
    )
    generated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)

    # Relationships
    submission: Mapped["Submission"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Submission", back_populates="report"
    )
    rule: Mapped["IntegrityRule | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "IntegrityRule", back_populates="reports"
    )
    case: Mapped["IntegrityCase | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "IntegrityCase", back_populates="report", uselist=False
    )
