"""
backend/schemas/reviewers.py

Pydantic v2 schemas for the Reviewer assignment and conflict endpoints
(Requirement 9).

    - ReviewerOut            (GET /reviewers list item)
    - PaginatedReviewers     (pagination envelope for GET /reviewers)
    - CaseReviewerCreate     (POST /cases/{case_id}/reviewers request body)
    - CaseReviewerOut        (CaseReviewer response row)
    - ConflictUpdate         (PATCH /cases/{case_id}/reviewers/{assignment_id}/conflict)

Validates: Requirements 9.1, 9.2, 9.6
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Response schemas (from_attributes so they can be built from ORM rows)
# ---------------------------------------------------------------------------


class ReviewerOut(BaseModel):
    """A single Reviewer record returned by GET /reviewers.

    Validates: Requirements 9.6
    """

    model_config = ConfigDict(from_attributes=True)

    reviewer_id: str
    full_name: str
    email: str
    reviewer_role: str
    status: str
    created_at: datetime


class CaseReviewerOut(BaseModel):
    """A CaseReviewer assignment row.

    Returned by POST /cases/{case_id}/reviewers and surfaced inside CaseDetail.
    Mirrors CaseReviewerSummary in cases.py but is the canonical reviewer-side
    definition.

    Validates: Requirements 9.1, 9.2
    """

    model_config = ConfigDict(from_attributes=True)

    assignment_id: int
    case_id: str
    reviewer_id: str
    assignment_role: str
    assigned_at: datetime
    unassigned_at: Optional[datetime] = None
    conflict_status: str
    conflict_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Request schemas (no from_attributes needed)
# ---------------------------------------------------------------------------


class CaseReviewerCreate(BaseModel):
    """Request body for POST /cases/{case_id}/reviewers.

    Validates: Requirements 9.1
    """

    reviewer_id: str
    assignment_role: str
    actor_role: str


class ConflictUpdate(BaseModel):
    """Request body for PATCH /cases/{case_id}/reviewers/{assignment_id}/conflict.

    Validates: Requirements 9.2
    """

    conflict_status: str
    conflict_reason: Optional[str] = None
    actor_role: str
    actor_ref: Optional[str] = None


# ---------------------------------------------------------------------------
# Pagination envelope
# ---------------------------------------------------------------------------


class PaginatedReviewers(BaseModel):
    """Pagination envelope for GET /reviewers.

    Validates: Requirements 9.6
    """

    items: List[ReviewerOut]
    total_count: int
    page: int
    page_size: int
