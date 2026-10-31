"""
backend/routers/reviewers.py

Thin FastAPI router for the Reviewer assignment and conflict endpoints
(Requirement 9).

Three path operations are exposed across **two** routers:

- ``GET /reviewers`` (on ``router``, mounted at ``/reviewers``) — paginated
  list of active reviewers (Requirement 9.6).
- ``POST /cases/{case_id}/reviewers`` (on ``case_reviewers_router``, mounted
  at ``/cases``) — assign a reviewer to a case (Requirement 9.1).
- ``PATCH /cases/{case_id}/reviewers/{assignment_id}/conflict`` (on
  ``case_reviewers_router``, mounted at ``/cases``) — declare a conflict on
  an assignment (Requirement 9.2).

Two routers are needed because the POST and PATCH endpoints live under the
``/cases`` namespace, not ``/reviewers``. ``main.py`` mounts ``router`` at
``prefix="/reviewers"`` and ``case_reviewers_router`` at ``prefix="/cases"``.

All business logic lives in the service layer
(``backend/services/case_service.py``). Routers are thin — they only parse
the request and call the appropriate service function, then own the
transaction boundary by committing on success.

Validates: Requirements 9.1, 9.2, 9.6, 21.3, 21.4
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.reviewers import (
    CaseReviewerCreate,
    CaseReviewerOut,
    ConflictUpdate,
    PaginatedReviewers,
)
from backend.services.case_service import (
    assign_reviewer,
    get_reviewers,
    update_conflict,
)

# Router for GET /reviewers — mounted at prefix="/reviewers" by main.py
router = APIRouter()

# Router for case-scoped endpoints — mounted at prefix="/cases" by main.py
case_reviewers_router = APIRouter()


# ── GET /reviewers — paginated list of active reviewers ─────────────────────


@router.get("", response_model=PaginatedReviewers)
def list_reviewers(
    page: int = Query(1, ge=1, description="1-based page number."),
    page_size: int = Query(20, ge=1, le=100, description="Maximum items per page."),
    db: Session = Depends(get_db),
) -> PaginatedReviewers:
    """Return a paginated list of active Reviewer records.

    Only reviewers with ``status = ACTIVE`` are returned. The pagination
    envelope includes ``total_count``, ``page``, and ``page_size``.

    Requirement 9.6 (endpoint exists; returns active reviewers with
    pagination envelope).
    """
    return get_reviewers(db, page=page, page_size=page_size)


# ── POST /cases/{case_id}/reviewers — assign a reviewer ─────────────────────


@case_reviewers_router.post(
    "/{case_id}/reviewers",
    response_model=CaseReviewerOut,
    status_code=201,
)
def post_reviewer(
    case_id: str,
    payload: CaseReviewerCreate,
    db: Session = Depends(get_db),
) -> CaseReviewerOut:
    """Assign a Reviewer to an IntegrityCase.

    Guards enforced by the service:
    - Case must exist (404 if not found).
    - Reviewer must exist (404 if not found).
    - Reviewer must be ACTIVE (422 if INACTIVE) (Requirement 21.3).
    - Reviewer must not have an active CONFLICT on the same case
      (409 if they do) (Requirement 9.5).

    Inserts a ``CaseReviewer`` record, a ``REVIEWER_ASSIGNED`` CaseEvent,
    and an AuditLog for the INSERT.

    Requirement 9.1 (endpoint exists).
    """
    result = assign_reviewer(db, case_id, payload)
    db.commit()
    return result


# ── PATCH /cases/{case_id}/reviewers/{assignment_id}/conflict ───────────────


@case_reviewers_router.patch(
    "/{case_id}/reviewers/{assignment_id}/conflict",
    response_model=CaseReviewerOut,
)
def patch_conflict(
    case_id: str,
    assignment_id: int,
    payload: ConflictUpdate,
    db: Session = Depends(get_db),
) -> CaseReviewerOut:
    """Declare a conflict on a CaseReviewer assignment.

    Guards enforced by the service:
    - Case must exist (404 if not found).
    - Assignment must exist and belong to the case (404 if not found).
    - Case must not be CLOSED (422 if CLOSED) (Requirement 21.4).

    Sets ``conflict_status = CONFLICT`` and ``unassigned_at`` to the
    current timestamp, inserts a ``REVIEWER_CONFLICT_DECLARED`` CaseEvent
    (Requirement 9.4), and writes an AuditLog for the UPDATE.

    Requirement 9.2 (endpoint exists), 9.3 (unassigned_at set).
    """
    result = update_conflict(db, case_id, assignment_id, payload)
    db.commit()
    return result
