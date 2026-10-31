"""
backend/routers/appeals.py

Thin FastAPI router for the Appeal and AppealReview endpoints (Requirement 12).

Endpoints (mounted with prefix="" in main.py so full paths are defined here):
- ``POST /cases/{case_id}/appeals``    — submit an appeal; HTTP 201
  (Requirements 12.1, 12.2)
- ``GET  /cases/{case_id}/appeals``    — list appeals for a case
  (Requirement 12.2)
- ``POST /appeals/{appeal_id}/reviews`` — submit an appeal review; HTTP 201
  (Requirement 12.3)

Routers are thin: call service, commit on success, return result.

Validates: Requirements 12.1, 12.2, 12.3
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.appeals import (
    AppealCreate,
    AppealOut,
    AppealReviewCreate,
    AppealReviewOut,
)
from backend.services import appeal_service

router = APIRouter()


# ── POST /cases/{case_id}/appeals — submit an appeal ────────────────────────


@router.post(
    "/cases/{case_id}/appeals",
    response_model=AppealOut,
    status_code=201,
)
def create_appeal(
    case_id: str,
    payload: AppealCreate,
    db: Session = Depends(get_db),
) -> AppealOut:
    """Submit an Appeal for an IntegrityCase.

    Returns HTTP 201 with the created AppealOut on success.
    Returns HTTP 404 if the case does not exist.

    Requirements 12.1 (endpoint exists and creates appeal),
    12.2 (returns AppealOut).
    """
    result = appeal_service.create_appeal(db, case_id, payload, actor=None)
    db.commit()
    return result


# ── GET /cases/{case_id}/appeals — list appeals ──────────────────────────────


@router.get(
    "/cases/{case_id}/appeals",
    response_model=list[AppealOut],
)
def list_appeals(
    case_id: str,
    db: Session = Depends(get_db),
) -> list[AppealOut]:
    """Return all Appeal records for an IntegrityCase ordered by
    ``submitted_at`` ascending.

    Returns HTTP 404 if the case does not exist.

    Requirement 12.2 (returns list[AppealOut] ordered by submitted_at asc).
    """
    return appeal_service.get_appeals(db, case_id)


# ── POST /appeals/{appeal_id}/reviews — submit an appeal review ─────────────


@router.post(
    "/appeals/{appeal_id}/reviews",
    response_model=AppealReviewOut,
    status_code=201,
)
def create_appeal_review(
    appeal_id: str,
    payload: AppealReviewCreate,
    db: Session = Depends(get_db),
) -> AppealReviewOut:
    """Submit an AppealReview for an Appeal.

    Returns HTTP 201 with the created AppealReviewOut on success.
    Returns HTTP 404 if the appeal does not exist.
    Returns HTTP 409 if the reviewer is the PRIMARY CaseReviewer for the
    linked case (Requirement 12.4).
    Returns HTTP 422 if outcome is UPHELD/OVERTURNED and
    independence_verified is False (Requirements 12.6, 21.1).

    Requirement 12.3 (endpoint exists and creates appeal review).
    """
    result = appeal_service.create_appeal_review(db, appeal_id, payload, actor=None)
    db.commit()
    return result
