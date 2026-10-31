"""
backend/models/case_event.py

SQLAlchemy ORM model for the CaseEvent table.
Immutable timeline of every status change and action taken on a case.
INSERT-only by convention — rows are never updated or deleted.
"""

from sqlalchemy import BigInteger, DateTime, ForeignKey, JSON, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class CaseEvent(Base):
    __tablename__ = "CaseEvent"

    event_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(
        VARCHAR(30), ForeignKey("IntegrityCase.case_id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    actor_role: Mapped[str] = mapped_column(VARCHAR(30), nullable=False)
    actor_ref: Mapped[str | None] = mapped_column(VARCHAR(30), nullable=True)
    previous_status: Mapped[str | None] = mapped_column(VARCHAR(40), nullable=True)
    new_status: Mapped[str | None] = mapped_column(VARCHAR(40), nullable=True)
    event_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)

    # Relationships
    case: Mapped["IntegrityCase"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "IntegrityCase", back_populates="events"
    )
