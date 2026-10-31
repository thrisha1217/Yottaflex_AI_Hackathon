"""
backend/models/learner.py

SQLAlchemy ORM model for the Learner table.
"""

from sqlalchemy import VARCHAR, DateTime, Enum, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Learner(Base):
    __tablename__ = "Learner"

    learner_id: Mapped[str] = mapped_column(VARCHAR(20), primary_key=True)
    full_name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    email: Mapped[str] = mapped_column(VARCHAR(150), unique=True, nullable=False)
    program: Mapped[str | None] = mapped_column(VARCHAR(100), nullable=True)
    year_of_study: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("ACTIVE", "INACTIVE", name="learner_status_enum"),
        default="ACTIVE",
        server_default="ACTIVE",
        nullable=False,
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)

    # Relationships
    submissions: Mapped[list["Submission"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Submission", back_populates="learner"
    )
