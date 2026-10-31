"""
backend/models/decision_evidence.py

SQLAlchemy ORM model for the DecisionEvidence bridge table.
Records which evidence items were considered in each decision.
"""

from sqlalchemy import BigInteger, ForeignKey, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class DecisionEvidence(Base):
    __tablename__ = "DecisionEvidence"

    decision_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("Decision.decision_id"), primary_key=True
    )
    evidence_id: Mapped[str] = mapped_column(
        VARCHAR(80), ForeignKey("EvidenceItem.evidence_id"), primary_key=True
    )

    # Relationships
    decision: Mapped["Decision"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Decision", back_populates="decision_evidence"
    )
    evidence_item: Mapped["EvidenceItem"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "EvidenceItem", back_populates="decision_evidence"
    )
