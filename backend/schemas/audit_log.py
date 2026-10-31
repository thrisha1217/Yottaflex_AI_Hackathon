"""
backend/schemas/audit_log.py

Pydantic v2 schemas for the AuditLog API endpoints (Requirement 13).

    - AuditLogOut        (single AuditLog row)
    - PaginatedAuditLog  (pagination envelope for GET /audit-log)

Validates: Requirements 13.1, 13.2, 13.3
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Response schemas (from_attributes so they can be built from ORM rows)
# ---------------------------------------------------------------------------


class AuditLogOut(BaseModel):
    """A single AuditLog record returned by the audit-log endpoints.

    ``old_values`` and ``new_values`` are JSON snapshots captured at the
    time of the INSERT/UPDATE operation (Requirement 13.5).

    Validates: Requirements 13.1, 13.3
    """

    model_config = ConfigDict(from_attributes=True)

    audit_id: int
    entity_type: str
    entity_id: str
    action: str
    actor_role: str
    actor_ref: Optional[str] = None
    old_values: Optional[dict] = None
    new_values: Optional[dict] = None
    created_at: datetime


class PaginatedAuditLog(BaseModel):
    """Pagination envelope for ``GET /audit-log``.

    ``items`` holds ``AuditLogOut`` rows for the requested page.
    ``total_count`` is the total number of matching rows (before paging)
    so clients can render page controls. ``len(items) <= page_size``.

    Validates: Requirements 13.1, 13.2, 13.3
    """

    items: List[AuditLogOut]
    total_count: int
    page: int
    page_size: int
