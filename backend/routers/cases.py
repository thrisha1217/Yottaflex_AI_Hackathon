"""
backend/routers/cases.py

Thin FastAPI router for the Integrity Case management endpoints
(Requirement 8).

Three path operations are exposed (mounted under ``/cases`` by main.py):
- ``GET /cases``                       — paginated, filtered case list
  (Requirements 8.1, 8.7).
- ``GET /cases/{case_id}``             — full case detail; 404 if not found
  (Requirement 8.2).
- ``PATCH /cases/{case_id}/status``   — update case status; 404 if not found,
  422 on invalid transition (Requirement 8.3).

Routers do not contain SQL; every query and business rule lives in the
service layer (``backend/services/case_service.py``). Each path operation
receives the SQLAlchemy session via ``Depends(get_db)`` and delegates to a
single service function, returning the appropriate Pydantic schema through
``response_model``.

Validates: Requirements 8.1, 8.2, 8.3, 8.7
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.cases import (
    CaseDetail,
    CaseStatus,
    CaseStatusUpdate,
    PaginatedCases,
    Priority,
)
from backend.services.case_service import (
    get_cases,
    get_case_detail,
    update_case_status,
)

router = APIRouter()


# ── GET /cases — paginated, filtered list ────────────────────────────────────


@router.get("", response_model=PaginatedCases)
def list_cases(
    status: CaseStatus | None = Query(
        None, description="Filter cases by lifecycle status."
    ),
    priority: Priority | None = Query(
        None, description="Filter cases by priority level."
    ),
    assigned_reviewer_id: str | None = Query(
        None, description="Filter to cases assigned to this reviewer_id."
    ),
    page: int = Query(1, ge=1, description="1-based page number."),
    page_size: int = Query(20, ge=1, le=100, description="Maximum items per page."),
    db: Session = Depends(get_db),
) -> PaginatedCases:
    """Return a paginated, filtered list of IntegrityCase records.

    Supports optional filtering by ``status``, ``priority``, and
    ``assigned_reviewer_id``. Each ``CaseSummary`` includes the computed
    ``has_conflict`` field.

    Requirements 8.1 (endpoint exists with pagination envelope), 8.7
    (filter by status, priority, and assigned reviewer).
    """
    return get_cases(
        db,
        status=status,
        priority=priority,
        assigned_reviewer_id=assigned_reviewer_id,
        page=page,
        page_size=page_size,
    )


# ── GET /cases/{case_id} — full case detail ─────────────────────────────────


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
) -> CaseDetail:
    """Return the full IntegrityCase record including linked SimilarityReport
    summary, assigned reviewers, decision summary if present, and the event
    timeline.

    Requirement 8.2 (endpoint exists). The service raises ``HTTPException``
    with status 404 when the ``case_id`` does not exist — the structured
    ``{"detail": "..."}`` response is produced automatically by FastAPI.
    """
    return get_case_detail(db, case_id)


# ── PATCH /cases/{case_id}/status — update case status ──────────────────────


@router.patch("/{case_id}/status", response_model=CaseDetail)
def patch_case_status(
    case_id: str,
    payload: CaseStatusUpdate,
    db: Session = Depends(get_db),
) -> CaseDetail:
    """Update the ``case_status`` of an IntegrityCase.

    The service inserts a ``STATUS_CHANGED`` CaseEvent (Requirement 8.4) and
    writes an AuditLog for the IntegrityCase UPDATE. It enforces valid status
    transitions, raising ``HTTPException`` with status 422 on invalid
    transition (Requirement 8.6) and 404 if the case is not found
    (Requirement 8.5).

    Requirement 8.3 (endpoint exists and accepts CaseStatusUpdate body).
    """
    return update_case_status(db, case_id, payload)
