"""
backend/models/integrity_rule.py

SQLAlchemy ORM model for the IntegrityRule table.
"""

from sqlalchemy import VARCHAR, Boolean, Date, Enum, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class IntegrityRule(Base):
    __tablename__ = "IntegrityRule"

    rule_id: Mapped[str] = mapped_column(VARCHAR(20), primary_key=True)
    rule_name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    min_similarity: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    max_similarity: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    action_type: Mapped[str] = mapped_column(
        Enum(
            "NO_REVIEW",
            "MONITOR",
            "REVIEW",
            "HIGH_PRIORITY_REVIEW",
            name="integrity_action_type_enum",
        ),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[Date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )

    # Relationships
    reports: Mapped[list["SimilarityReport"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "SimilarityReport", back_populates="rule"
    )
