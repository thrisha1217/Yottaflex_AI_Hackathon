"""
backend/models/decision.py

SQLAlchemy ORM model for the Decision table.
Records investigation outcomes. Immutable once inserted; new rows
with previous_decision_id links replace superseded decisions.
"""

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Text, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Decision(Base):
    __tablename__ = "Decision"

    decision_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(
        VARCHAR(30), ForeignKey("IntegrityCase.case_id"), nullable=False
    )
    reviewer_id: Mapped[str] = mapped_column(
        VARCHAR(20), ForeignKey("Reviewer.reviewer_id"), nullable=False
    )
    previous_decision_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("Decision.decision_id"), nullable=True
    )
    decision_outcome: Mapped[str] = mapped_column(
        Enum("NO_VIOLATION", "VIOLATION", "INCONCLUSIVE", name="decision_outcome_enum"),
        nullable=False,
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    decided_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    is_final: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )

    # Relationships
    case: Mapped["IntegrityCase"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "IntegrityCase", back_populates="decisions"
    )
    reviewer: Mapped["Reviewer"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Reviewer", back_populates="decisions"
    )
    decision_evidence: Mapped[list["DecisionEvidence"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "DecisionEvidence", back_populates="decision"
    )
