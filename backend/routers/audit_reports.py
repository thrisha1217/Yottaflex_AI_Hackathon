"""
backend/routers/audit_reports.py

FastAPI router for the Audit and Compliance Reporting endpoints (Requirement 20).

Mounted at prefix="/audit" in main.py.

Endpoints
---------
GET /audit/conflict-reassignments             – Req 20.1
GET /audit/post-decision-evidence             – Req 20.2
GET /audit/appeals-without-independent-review – Req 20.3
GET /audit/case-event-log/{case_id}           – Req 20.6
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.audit_reports import (
    AppealsWithoutReviewOut,
    ConflictReassignmentOut,
    PostDecisionEvidenceOut,
)
from backend.schemas.cases import CaseEventOut
from backend.services import audit_reports_service

router = APIRouter(tags=["Audit Reports"])


@router.get(
    "/conflict-reassignments",
    response_model=list[ConflictReassignmentOut],
    summary="All CaseReviewer records where conflict_status = CONFLICT",
)
def get_conflict_reassignments(
    db: Session = Depends(get_db),
) -> list[ConflictReassignmentOut]:
    """Return all reviewer assignments that were flagged as a conflict of interest.

    Validates: Requirements 20.1
    """
    return audit_reports_service.conflict_reassignments(db)


@router.get(
    "/post-decision-evidence",
    response_model=list[PostDecisionEvidenceOut],
    summary="Non-material evidence items (added after case closure) grouped by case",
)
def get_post_decision_evidence(
    db: Session = Depends(get_db),
) -> list[PostDecisionEvidenceOut]:
    """Return EvidenceItem rows where is_material = FALSE, grouped by case_id.

    Validates: Requirements 20.2
    """
    return audit_reports_service.post_decision_evidence(db)


@router.get(
    "/appeals-without-independent-review",
    response_model=list[AppealsWithoutReviewOut],
    summary="Appeals with UPHELD/OVERTURNED status but no independent AppealReview",
)
def get_appeals_without_independent_review(
    db: Session = Depends(get_db),
) -> list[AppealsWithoutReviewOut]:
    """Return appeals that have a resolved status but lack an
    AppealReview with independence_verified = TRUE.

    By design this list should always be empty — the API enforces the
    independence guard at write time. This endpoint surfaces any violations.

    Validates: Requirements 20.3
    """
    return audit_reports_service.appeals_without_independent_review(db)


@router.get(
    "/case-event-log/{case_id}",
    response_model=list[CaseEventOut],
    summary="Full CaseEvent timeline for one case in ascending occurred_at order",
)
def get_case_event_log(
    case_id: str,
    db: Session = Depends(get_db),
) -> list[CaseEventOut]:
    """Return the complete CaseEvent timeline for an IntegrityCase.

    Returns HTTP 404 if the case does not exist.

    Validates: Requirements 20.6
    """
    return audit_reports_service.case_event_log(db, case_id)
