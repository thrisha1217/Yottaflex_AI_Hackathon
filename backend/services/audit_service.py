"""
backend/services/audit_service.py

Foundation audit service for the Academic Integrity System backend.

This module is the single place every other service calls to record
data-level changes (AuditLog) and case-level timeline events (CaseEvent).

Design contract
---------------
* Every function receives the caller's SQLAlchemy ``Session`` and writes a
  row via ``db.add()`` **without committing**. The transaction boundary is
  owned by the router layer — services never call ``db.commit()`` or
  ``db.flush()``. This keeps AuditLog/CaseEvent writes in the same
  transaction as the business record they describe, so a failed rollback
  cleans up both the data and its audit trail together.

* ``log_insert`` writes an AuditLog with ``action="INSERT"`` and
  ``old_values=None``.

* ``log_update`` writes an AuditLog with ``action="UPDATE"`` and a
  non-null ``old_values`` snapshot captured before the update is flushed.

* ``insert_case_event`` writes an INSERT-only CaseEvent row capturing the
  previous/new case status for the case timeline. CaseEvent rows are never
  updated or deleted.

* ``query_audit_log`` returns a paginated, filtered view of AuditLog rows
  ordered by ``created_at`` descending (Requirements 13.1, 13.2, 13.3).

Requirements validated: 13.1, 13.2, 13.3, 13.4, 13.5
"""

from datetime import date, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.audit_log import AuditLog
from backend.models.case_event import CaseEvent
from backend.schemas.audit_log import AuditLogOut, PaginatedAuditLog


def log_insert(
    db: Session,
    entity_type: str,
    entity_id: str,
    new_values: dict,
    actor_role: str,
    actor_ref: str | None = None,
) -> None:
    """Write an AuditLog row for an INSERT operation.

    ``old_values`` is always ``None`` for inserts (there was no prior state),
    and ``new_values`` carries the JSON snapshot of the created row.

    The row is added to the session but **not committed** — the caller owns
    the transaction boundary.

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        entity_type: Name of the affected table (e.g. ``"IntegrityCase"``).
        entity_id: Primary key value of the affected row.
        new_values: JSON-compatible dict of the inserted column values.
        actor_role: Role performing the action (e.g. ``"SYSTEM"``).
        actor_ref: Optional reference id of the actor (e.g. ``"REV-001"``).
    """
    db.add(
        AuditLog(
            entity_type=entity_type,
            entity_id=str(entity_id),
            action="INSERT",
            actor_role=actor_role,
            actor_ref=actor_ref,
            old_values=None,
            new_values=new_values,
            created_at=datetime.utcnow(),
        )
    )


def log_update(
    db: Session,
    entity_type: str,
    entity_id: str,
    old_values: dict,
    new_values: dict,
    actor_role: str,
    actor_ref: str | None = None,
) -> None:
    """Write an AuditLog row for an UPDATE operation.

    ``old_values`` MUST be a non-null dict — the snapshot of the row's
    column values captured *before* the update is flushed. ``new_values``
    carries the post-update column values. Both are serialised as JSON.

    The row is added to the session but **not committed**.

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        entity_type: Name of the affected table (e.g. ``"Decision"``).
        entity_id: Primary key value of the affected row.
        old_values: Non-null JSON-compatible dict of the prior column values.
        new_values: JSON-compatible dict of the post-update column values.
        actor_role: Role performing the action (e.g. ``"REVIEWER"``).
        actor_ref: Optional reference id of the actor.
    """
    db.add(
        AuditLog(
            entity_type=entity_type,
            entity_id=str(entity_id),
            action="UPDATE",
            actor_role=actor_role,
            actor_ref=actor_ref,
            old_values=old_values,
            new_values=new_values,
            created_at=datetime.utcnow(),
        )
    )


def insert_case_event(
    db: Session,
    case_id: str,
    event_type: str,
    actor_role: str,
    prev_status: str | None = None,
    new_status: str | None = None,
    details: dict | None = None,
    actor_ref: str | None = None,
) -> None:
    """Insert an INSERT-only CaseEvent row for a case timeline.

    CaseEvent rows record every status change and meaningful action on an
    IntegrityCase. They are append-only — never updated or deleted — and are
    written within the same transaction as the triggering operation so the
    timeline never diverges from reality.

    The row is added to the session but **not committed**.

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        case_id: The ``case_id`` of the affected IntegrityCase.
        event_type: The event type (e.g. ``"CASE_CREATED"``,
            ``"STATUS_CHANGED"``, ``"DECISION_RECORDED"``).
        actor_role: Role performing the action.
        prev_status: The case status before the change, if any.
        new_status: The case status after the change, if any.
        details: Optional JSON-compatible dict of extra event details.
        actor_ref: Optional reference id of the actor.
    """
    db.add(
        CaseEvent(
            case_id=case_id,
            event_type=event_type,
            actor_role=actor_role,
            actor_ref=actor_ref,
            previous_status=prev_status,
            new_status=new_status,
            event_details=details,
            occurred_at=datetime.utcnow(),
        )
    )


def query_audit_log(
    db: Session,
    entity_type: str | None,
    from_date: date | None,
    to_date: date | None,
    page: int,
    page_size: int,
) -> PaginatedAuditLog:
    """Return a paginated, filtered list of AuditLog rows ordered by
    ``created_at`` descending.

    Filters are all optional and are combined with AND when supplied:

    * ``entity_type`` — exact match on ``AuditLog.entity_type``.
    * ``from_date``   — inclusive lower bound on ``AuditLog.created_at``
                        (compared against the start of the given day, i.e.
                        ``datetime(from_date.year, from_date.month,
                        from_date.day, 0, 0, 0)``).
    * ``to_date``     — inclusive upper bound on ``AuditLog.created_at``
                        (compared against the end of the given day, i.e.
                        ``datetime(to_date.year, to_date.month,
                        to_date.day, 23, 59, 59)``).

    Args:
        db:          Active SQLAlchemy session.
        entity_type: Optional entity type filter (exact match).
        from_date:   Optional inclusive start date filter.
        to_date:     Optional inclusive end date filter.
        page:        1-based page number.
        page_size:   Maximum number of rows to return per page.

    Returns:
        ``PaginatedAuditLog`` with ``items``, ``total_count``, ``page``,
        and ``page_size``.

    Validates: Requirements 13.1, 13.2, 13.3
    """
    query = db.query(AuditLog)

    if entity_type is not None:
        query = query.filter(AuditLog.entity_type == entity_type)

    if from_date is not None:
        from_dt = datetime(from_date.year, from_date.month, from_date.day, 0, 0, 0)
        query = query.filter(AuditLog.created_at >= from_dt)

    if to_date is not None:
        to_dt = datetime(to_date.year, to_date.month, to_date.day, 23, 59, 59)
        query = query.filter(AuditLog.created_at <= to_dt)

    total_count: int = query.with_entities(func.count(AuditLog.audit_id)).scalar()

    rows = (
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedAuditLog(
        items=[AuditLogOut.model_validate(row) for row in rows],
        total_count=total_count,
        page=page,
        page_size=page_size,
    )
