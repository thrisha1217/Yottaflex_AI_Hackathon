"""
backend/models/audit_log.py

SQLAlchemy ORM model for the AuditLog table.
Application-wide change log capturing every INSERT, UPDATE and DELETE
on sensitive tables with before/after value snapshots.
"""

from sqlalchemy import BigInteger, DateTime, JSON, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class AuditLog(Base):
    __tablename__ = "AuditLog"

    audit_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(VARCHAR(80), nullable=False)
    action: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    actor_role: Mapped[str] = mapped_column(VARCHAR(30), nullable=False)
    actor_ref: Mapped[str | None] = mapped_column(VARCHAR(30), nullable=True)
    old_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
