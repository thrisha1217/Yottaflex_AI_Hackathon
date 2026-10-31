"""
backend/schemas/cases.py

Pydantic v2 schemas for the Integrity Case management endpoints.

Covers:
    - CaseStatus / Priority enums
    - CaseStatusUpdate          (PATCH /cases/{case_id}/status request body)
    - CaseSummary               (list item with computed has_conflict)
    - CaseDetail                (full record with report, reviewers, decision, events)
    - PaginatedCases            (pagination envelope for GET /cases)
    - CaseEventOut              (single timeline event)
    - CaseReviewerSummary       (reviewer assignment summary)
    - DecisionSummary           (decision outcome summary)

Requirements validated: 8.1, 8.2, 8.3
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CaseStatus(str, Enum):
    """Lifecycle status of an IntegrityCase."""

    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    AWAITING_INFORMATION = "AWAITING_INFORMATION"
    DECIDED = "DECIDED"
    APPEAL_PENDING = "APPEAL_PENDING"
    CLOSED = "CLOSED"


class Priority(str, Enum):
    """Priority level of an IntegrityCase."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# ---------------------------------------------------------------------------
# SimilarityReportSummary
#
# Prefer importing from backend.schemas.submissions so there is a single
# canonical definition. If that module has not been created yet (task 10.1),
# fall back to a local definition with the fields needed by CaseDetail.
# ---------------------------------------------------------------------------

try:
    from backend.schemas.submissions import SimilarityReportSummary  # noqa: F401
except ImportError:  # pragma: no cover — fallback until submissions.py exists

    class SimilarityReportSummary(BaseModel):
        """Fallback definition; replaced by submissions.py when available."""

        model_config = ConfigDict(from_attributes=True)

        report_id: str
        submission_id: str
        similarity_score: float
        review_required: bool
        report_status: str
        generated_at: datetime


# ---------------------------------------------------------------------------
# Nested output schemas
# ---------------------------------------------------------------------------


class CaseEventOut(BaseModel):
    """A single CaseEvent row in the case timeline."""

    model_config = ConfigDict(from_attributes=True)

    event_id: int
    case_id: str
    event_type: str
    actor_role: str
    actor_ref: Optional[str] = None
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    event_details: Optional[dict] = None
    occurred_at: datetime


class CaseReviewerSummary(BaseModel):
    """Summary of a reviewer assignment on a case."""

    model_config = ConfigDict(from_attributes=True)

    assignment_id: int
    case_id: str
    reviewer_id: str
    assignment_role: str
    assigned_at: datetime
    unassigned_at: Optional[datetime] = None
    conflict_status: str
    conflict_reason: Optional[str] = None


class DecisionSummary(BaseModel):
    """Summary of a decision recorded on a case."""

    model_config = ConfigDict(from_attributes=True)

    decision_id: int
    case_id: str
    decision_outcome: str
    rationale: str
    decided_at: datetime
    is_final: bool


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class CaseStatusUpdate(BaseModel):
    """Request body for PATCH /cases/{case_id}/status.

    Validates: Requirements 8.3
    """

    case_status: CaseStatus
    actor_role: str
    actor_ref: Optional[str] = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class CaseSummary(BaseModel):
    """Summary fields for a case list item.

    ``has_conflict`` is computed by the service layer: True when any
    CaseReviewer on the case has ``conflict_status = CONFLICT``.

    Validates: Requirements 8.1
    """

    model_config = ConfigDict(from_attributes=True)

    case_id: str
    case_status: CaseStatus
    priority: str
    opened_at: datetime
    closed_at: Optional[datetime] = None
    has_conflict: bool = False


class CaseDetail(CaseSummary):
    """Full case record with linked report, reviewers, decision, and events.

    Validates: Requirements 8.2
    """

    report_summary: SimilarityReportSummary
    reviewers: List[CaseReviewerSummary] = []
    decision_summary: Optional[DecisionSummary] = None
    events: List[CaseEventOut] = []


class PaginatedCases(BaseModel):
    """Pagination envelope for GET /cases.

    Validates: Requirements 8.1
    """

    items: List[CaseSummary]
    total_count: int
    page: int
    page_size: int
