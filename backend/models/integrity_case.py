"""
backend/models/integrity_case.py

SQLAlchemy ORM model for the IntegrityCase table.
"""

from sqlalchemy import VARCHAR, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class IntegrityCase(Base):
    __tablename__ = "IntegrityCase"

    case_id: Mapped[str] = mapped_column(VARCHAR(30), primary_key=True)
    report_id: Mapped[str] = mapped_column(
        VARCHAR(80), ForeignKey("SimilarityReport.report_id"), unique=True, nullable=False
    )
    case_status: Mapped[str] = mapped_column(
        Enum(
            "OPEN",
            "UNDER_REVIEW",
            "AWAITING_INFORMATION",
            "DECIDED",
            "APPEAL_PENDING",
            "CLOSED",
            name="case_status_enum",
        ),
        default="OPEN",
        server_default="OPEN",
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(
        Enum("LOW", "MEDIUM", "HIGH", name="case_priority_enum"),
        default="MEDIUM",
        server_default="MEDIUM",
        nullable=False,
    )
    opened_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    closed_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    report: Mapped["SimilarityReport"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "SimilarityReport", back_populates="case"
    )
    reviewers: Mapped[list["CaseReviewer"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "CaseReviewer", back_populates="case"
    )
    evidence_items: Mapped[list["EvidenceItem"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "EvidenceItem", back_populates="case"
    )
    decisions: Mapped[list["Decision"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Decision", back_populates="case"
    )
    appeals: Mapped[list["Appeal"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Appeal", back_populates="case"
    )
    events: Mapped[list["CaseEvent"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "CaseEvent",
        back_populates="case",
        order_by="CaseEvent.occurred_at",
    )
