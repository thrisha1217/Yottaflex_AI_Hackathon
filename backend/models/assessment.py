"""
backend/models/assessment.py

SQLAlchemy ORM model for the Assessment table.
"""

from sqlalchemy import VARCHAR, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Assessment(Base):
    __tablename__ = "Assessment"

    assessment_id: Mapped[str] = mapped_column(VARCHAR(20), primary_key=True)
    title: Mapped[str] = mapped_column(VARCHAR(200), nullable=False)
    course_code: Mapped[str] = mapped_column(VARCHAR(30), nullable=False)
    assessment_type: Mapped[str] = mapped_column(
        Enum("ASSIGNMENT", "EXAM", "PROJECT", "QUIZ", name="assessment_type_enum"),
        nullable=False,
    )
    due_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("DRAFT", "ACTIVE", "CLOSED", name="assessment_status_enum"),
        default="DRAFT",
        server_default="DRAFT",
        nullable=False,
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)

    # Relationships
    submissions: Mapped[list["Submission"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Submission", back_populates="assessment"
    )
