"""
backend/schemas/audit_reports.py

Pydantic v2 schemas for the Audit and Compliance Reporting endpoints
(Requirement 20).

    - EvidenceItemSummary        (nested evidence summary item)
    - ConflictReassignmentOut    (GET /audit/conflict-reassignments)
    - PostDecisionEvidenceOut    (GET /audit/post-decision-evidence)
    - AppealsWithoutReviewOut    (GET /audit/appeals-without-independent-review)

``CaseEventOut`` is imported from ``backend.schemas.cases`` to avoid
duplication; it is used by ``GET /audit/case-event-log/{case_id}``.

Validates: Requirements 20.1, 20.2, 20.3, 20.6
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from backend.schemas.cases import CaseEventOut  # noqa: F401 — re-exported


# ---------------------------------------------------------------------------
# Nested data items
# ---------------------------------------------------------------------------


class EvidenceItemSummary(BaseModel):
    """Minimal EvidenceItem summary used inside post-decision evidence lists.

    Only the fields relevant to the compliance report are surfaced — the
    full ``EvidenceItemOut`` (with ``added_by_role``, ``evidence_reference``,
    etc.) lives in ``backend.schemas.evidence``.
    """

    model_config = ConfigDict(from_attributes=True)

    evidence_id: str
    evidence_type: str
    description: str
    added_at: datetime
    is_material: bool


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ConflictReassignmentOut(BaseModel):
    """A CaseReviewer row with ``conflict_status = CONFLICT``.

    ``reviewer_name`` is resolved from the linked Reviewer record by the
    service layer. ``conflict_reason`` and ``unassigned_at`` are populated
    when the conflict was declared.

    Validates: Requirements 20.1
    """

    model_config = ConfigDict(from_attributes=True)

    assignment_id: int
    case_id: str
    reviewer_id: str
    reviewer_name: str
    conflict_reason: Optional[str] = None
    assigned_at: datetime
    unassigned_at: Optional[datetime] = None


class PostDecisionEvidenceOut(BaseModel):
    """Evidence items added to a case after its Decision was recorded.

    Groups all non-material (``is_material = FALSE``) EvidenceItem records
    for a single case.

    Validates: Requirements 20.2
    """

    case_id: str
    evidence: List[EvidenceItemSummary]


class AppealsWithoutReviewOut(BaseModel):
    """An Appeal with ``appeal_status`` UPHELD or OVERTURNED but no
    independent AppealReview (``independence_verified = TRUE``).

    Validates: Requirements 20.3
    """

    model_config = ConfigDict(from_attributes=True)

    appeal_id: str
    case_id: str
    appeal_status: str
    submitted_at: datetime
