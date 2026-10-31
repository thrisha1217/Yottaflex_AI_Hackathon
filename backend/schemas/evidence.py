"""
backend/schemas/evidence.py

Pydantic v2 schemas for the EvidenceItem endpoints (Requirement 10).

    - EvidenceItemCreate  (POST /cases/{case_id}/evidence request body)
    - EvidenceItemOut     (EvidenceItem response row)

Validates: Requirements 10.1, 10.2
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Request schemas (no from_attributes needed)
# ---------------------------------------------------------------------------


class EvidenceItemCreate(BaseModel):
    """Request body for POST /cases/{case_id}/evidence.

    ``actor_role`` / ``actor_ref`` capture the requesting user context for
    audit logging and CaseEvent insertion; they are not persisted as columns
    on EvidenceItem.

    Validates: Requirements 10.1
    """

    evidence_type: str
    description: str
    evidence_reference: Optional[str] = None
    added_by_role: str
    added_by_ref: Optional[str] = None
    actor_role: str


# ---------------------------------------------------------------------------
# Response schemas (from_attributes so they can be built from ORM rows)
# ---------------------------------------------------------------------------


class EvidenceItemOut(BaseModel):
    """An EvidenceItem record returned by the evidence endpoints.

    Validates: Requirements 10.2
    """

    model_config = ConfigDict(from_attributes=True)

    evidence_id: str
    case_id: str
    evidence_type: str
    description: str
    evidence_reference: Optional[str] = None
    added_by_role: str
    added_by_ref: Optional[str] = None
    added_at: datetime
    is_material: bool
