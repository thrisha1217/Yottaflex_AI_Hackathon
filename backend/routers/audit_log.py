"""
backend/routers/audit_log.py

FastAPI router for the Audit Log query endpoint (Requirement 13).

One path operation is exposed (mounted under ``/audit-log`` by main.py):

- ``GET /audit-log`` — paginated, filtered audit log list ordered by
  ``created_at`` descending (Requirements 13.1, 13.2, 13.3).

The router does not contain SQL; all query logic lives in
``backend/services/audit_service.query_audit_log``. The session is
injected via ``Depends(get_db)``.

Validates: Requirements 13.1, 13.2, 13.3
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.audit_log import PaginatedAuditLog
from backend.services.audit_service import query_audit_log

router = APIRouter()


# ── GET /audit-log — paginated, filtered audit log ───────────────────────────


@router.get("", response_model=PaginatedAuditLog)
def list_audit_log(
    entity_type: str | None = Query(
        None, description="Filter by entity type (exact match)."
    ),
    from_date: date | None = Query(
        None, description="Inclusive lower bound on created_at (YYYY-MM-DD)."
    ),
    to_date: date | None = Query(
        None, description="Inclusive upper bound on created_at (YYYY-MM-DD)."
    ),
    page: int = Query(1, ge=1, description="1-based page number."),
    page_size: int = Query(20, ge=1, le=100, description="Maximum items per page."),
    db: Session = Depends(get_db),
) -> PaginatedAuditLog:
    """Return a paginated list of AuditLog records ordered by ``created_at``
    descending.

    All filter parameters are optional and are combined with AND:

    - ``entity_type`` — exact match on the ``entity_type`` field.
    - ``from_date``   — keep rows where ``created_at >= from_date`` (start of day).
    - ``to_date``     — keep rows where ``created_at <= to_date`` (end of day).

    The response envelope includes ``items``, ``total_count``, ``page``, and
    ``page_size`` so clients can render pagination controls.

    Requirements 13.1 (endpoint exists), 13.2 (pagination envelope),
    13.3 (filter and sort behaviour).
    """
    return query_audit_log(
        db,
        entity_type=entity_type,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
