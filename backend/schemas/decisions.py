"""
backend/schemas/decisions.py

Pydantic v2 schemas for the Decision endpoints (Requirement 11).

    - DecisionCreate  (POST /cases/{case_id}/decisions request body)
    - DecisionOut     (Decision response row)

Validates: Requirements 11.1, 11.2, 11.6
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Request schemas (no from_attributes needed)
# ---------------------------------------------------------------------------


class DecisionCreate(BaseModel):
    """Request body for POST /cases/{case_id}/decisions.

    ``evidence_ids`` is the array of EvidenceItem IDs to link via
    DecisionEvidence rows (Requirement 11.6). ``actor_role`` captures the
    requesting user context for audit logging.

    Validates: Requirements 11.1, 11.6
    """

    reviewer_id: str
    decision_outcome: str
    rationale: str
    previous_decision_id: Optional[int] = None
    evidence_ids: List[str] = []
    actor_role: str


# ---------------------------------------------------------------------------
# Response schemas (from_attributes so they can be built from ORM rows)
# ---------------------------------------------------------------------------


class DecisionOut(BaseModel):
    """A Decision record returned by the decision endpoints.

    Validates: Requirements 11.2
    """

    model_config = ConfigDict(from_attributes=True)

    decision_id: int
    case_id: str
    reviewer_id: str
    previous_decision_id: Optional[int] = None
    decision_outcome: str
    rationale: str
    decided_at: datetime
    is_final: bool
