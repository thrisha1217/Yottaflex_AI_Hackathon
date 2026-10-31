"""
backend/models/evidence_item.py

SQLAlchemy ORM model for the EvidenceItem table.
"""

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Text, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class EvidenceItem(Base):
    __tablename__ = "EvidenceItem"

    evidence_id: Mapped[str] = mapped_column(VARCHAR(80), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        VARCHAR(30), ForeignKey("IntegrityCase.case_id"), nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(
        Enum(
            "SIMILARITY_MATCH",
            "QUOTATION",
            "TEMPLATE",
            "STUDENT_EXPLANATION",
            "DOCUMENT",
            "OTHER",
            name="evidence_type_enum",
        ),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(VARCHAR(255), nullable=True)
    added_by_role: Mapped[str] = mapped_column(
        Enum(
            "LEARNER",
            "INSTRUCTOR",
            "REVIEWER",
            "ACADEMIC_ADMIN",
            "SYSTEM",
            name="evidence_added_by_role_enum",
        ),
        nullable=False,
    )
    added_by_ref: Mapped[str | None] = mapped_column(VARCHAR(30), nullable=True)
    added_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    is_material: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )

    # Relationships
    case: Mapped["IntegrityCase"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "IntegrityCase", back_populates="evidence_items"
    )
    decision_evidence: Mapped[list["DecisionEvidence"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "DecisionEvidence", back_populates="evidence_item"
    )
