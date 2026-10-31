"""
backend/models/case_reviewer.py

SQLAlchemy ORM model for the CaseReviewer bridge table.
"""

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Text, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class CaseReviewer(Base):
    __tablename__ = "CaseReviewer"

    assignment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(
        VARCHAR(30), ForeignKey("IntegrityCase.case_id"), nullable=False
    )
    reviewer_id: Mapped[str] = mapped_column(
        VARCHAR(20), ForeignKey("Reviewer.reviewer_id"), nullable=False
    )
    assignment_role: Mapped[str] = mapped_column(
        Enum("PRIMARY", "SECONDARY", "INDEPENDENT_APPEAL", name="assignment_role_enum"),
        nullable=False,
    )
    assigned_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    unassigned_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    conflict_status: Mapped[str] = mapped_column(
        Enum("PENDING", "CLEARED", "CONFLICT", name="conflict_status_enum"),
        default="PENDING",
        server_default="PENDING",
        nullable=False,
    )
    conflict_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    case: Mapped["IntegrityCase"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "IntegrityCase", back_populates="reviewers"
    )
    reviewer: Mapped["Reviewer"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Reviewer", back_populates="case_assignments"
    )
