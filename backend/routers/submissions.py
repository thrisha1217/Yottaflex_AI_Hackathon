"""
backend/routers/submissions.py

Thin FastAPI routers for the Submission and SimilarityReport read endpoints
(Requirement 7).

Two routers are exposed:
- ``router`` — mounted under ``/submissions`` for the submission list and
  detail endpoints (Requirements 7.1–7.5).
- ``similarity_router`` — mounted under ``/similarity-reports`` for the full
  similarity report endpoint (Requirement 7.6).

Routers do not contain SQL; every query and business rule lives in the
service layer (``backend/services/case_service.py``). Each path operation
receives the SQLAlchemy session via ``Depends(get_db)`` and delegates to a
single service function, returning the appropriate Pydantic schema through
``response_model``.

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.submissions import (
    PaginatedSubmissions,
    SubmissionDetail,
    SimilarityReportDetail,
)
from backend.services.case_service import (
    get_submissions,
    get_submission_detail,
    get_similarity_report,
)

# ── Submissions router (mounted at /submissions) ────────────────────────────

router = APIRouter()


@router.get("", response_model=PaginatedSubmissions)
def list_submissions(
    flagged: bool = Query(False, description="If true, return only submissions "
                              "whose linked report has review_required = True."),
    page: int = Query(1, ge=1, description="1-based page number."),
    page_size: int = Query(20, ge=1, le=100, description="Maximum items per page."),
    db: Session = Depends(get_db),
) -> PaginatedSubmissions:
    """Return a paginated list of submissions, optionally filtered to flagged.

    Requirements 7.1 (endpoint exists), 7.3 (flagged filter), 7.4 (pagination
    envelope with total_count, page, page_size).
    """
    return get_submissions(db, flagged=flagged, page=page, page_size=page_size)


@router.get("/{submission_id}", response_model=SubmissionDetail)
def get_submission(
    submission_id: str,
    db: Session = Depends(get_db),
) -> SubmissionDetail:
    """Return a single submission with its linked SimilarityReport.

    Requirement 7.2 (endpoint exists), 7.5 (404 with structured detail body
    when the submission_id does not exist — the service raises HTTPException).
    """
    return get_submission_detail(db, submission_id)


# ── Similarity reports router (mounted at /similarity-reports) ──────────────

similarity_router = APIRouter()


@similarity_router.get("/{report_id}", response_model=SimilarityReportDetail)
def get_report(
    report_id: str,
    db: Session = Depends(get_db),
) -> SimilarityReportDetail:
    """Return the full SimilarityReport including linked IntegrityRule details.

    Requirement 7.6 (endpoint exists and returns rule details). The service
    raises HTTPException with status 404 when the report_id does not exist.
    """
    return get_similarity_report(db, report_id)
