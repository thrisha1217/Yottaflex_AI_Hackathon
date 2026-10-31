"""
backend/schemas/appeals.py

Pydantic v2 schemas for the Appeal and AppealReview endpoints (Requirement 12).

    - AppealCreate        (POST /cases/{case_id}/appeals request body)
    - AppealOut           (Appeal response row)
    - AppealReviewCreate  (POST /appeals/{appeal_id}/reviews request body)
    - AppealReviewOut     (AppealReview response row)

Validates: Requirements 12.1, 12.3
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Request schemas (no from_attributes needed)
# ---------------------------------------------------------------------------


class AppealCreate(BaseModel):
    """Request body for POST /cases/{case_id}/appeals.

    Validates: Requirements 12.1
    """

    learner_id: str
    reason: str
    actor_role: str


class AppealReviewCreate(BaseModel):
    """Request body for POST /appeals/{appeal_id}/reviews.

    Validates: Requirements 12.3
    """

    reviewer_id: str
    outcome: str
    rationale: str
    independence_verified: bool
    actor_role: str


# ---------------------------------------------------------------------------
# Response schemas (from_attributes so they can be built from ORM rows)
# ---------------------------------------------------------------------------


class AppealOut(BaseModel):
    """An Appeal record returned by the appeal endpoints.

    Validates: Requirements 12.1, 12.2
    """

    model_config = ConfigDict(from_attributes=True)

    appeal_id: str
    case_id: str
    learner_id: str
    appeal_no: int
    reason: str
    submitted_at: datetime
    appeal_status: str
    resolved_at: Optional[datetime] = None


class AppealReviewOut(BaseModel):
    """An AppealReview record returned by the appeal review endpoint.

    Validates: Requirements 12.3
    """

    model_config = ConfigDict(from_attributes=True)

    review_id: int
    appeal_id: str
    reviewer_id: str
    outcome: str
    rationale: str
    independence_verified: bool
    reviewed_at: datetime
