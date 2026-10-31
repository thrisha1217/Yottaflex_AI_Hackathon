"""Verification that audit log schemas build from ORM-like objects via from_attributes.

Validates: Requirements 13.1, 13.2, 13.3
"""

from datetime import datetime

from backend.schemas.audit_log import (
    AuditLogOut,
    PaginatedAuditLog,
)


# ---------------------------------------------------------------------------
# Fake ORM-like objects
# ---------------------------------------------------------------------------


class FakeAuditLog:
    pass


# ---------------------------------------------------------------------------
# AuditLogOut (response — from_attributes)
# ---------------------------------------------------------------------------


def test_audit_log_out_from_orm():
    row = FakeAuditLog()
    row.audit_id = 1
    row.entity_type = "IntegrityCase"
    row.entity_id = "INT-2026-000001"
    row.action = "INSERT"
    row.actor_role = "SYSTEM"
    row.actor_ref = "REV-001"
    row.old_values = None
    row.new_values = {"case_status": "OPEN"}
    row.created_at = datetime(2026, 1, 15, 9, 0, 0)

    out = AuditLogOut.model_validate(row)
    assert out.audit_id == 1
    assert out.entity_type == "IntegrityCase"
    assert out.entity_id == "INT-2026-000001"
    assert out.action == "INSERT"
    assert out.actor_role == "SYSTEM"
    assert out.actor_ref == "REV-001"
    assert out.old_values is None
    assert out.new_values == {"case_status": "OPEN"}
    assert out.created_at == datetime(2026, 1, 15, 9, 0, 0)


def test_audit_log_out_nullable_fields():
    row = FakeAuditLog()
    row.audit_id = 2
    row.entity_type = "Decision"
    row.entity_id = "DEC-1"
    row.action = "UPDATE"
    row.actor_role = "REVIEWER"
    row.actor_ref = None
    row.old_values = {"is_final": False}
    row.new_values = {"is_final": True}
    row.created_at = datetime(2026, 1, 16, 10, 0, 0)

    out = AuditLogOut.model_validate(row)
    assert out.actor_ref is None
    assert out.old_values == {"is_final": False}
    assert out.new_values == {"is_final": True}


def test_audit_log_out_field_set():
    assert set(AuditLogOut.model_fields.keys()) == {
        "audit_id",
        "entity_type",
        "entity_id",
        "action",
        "actor_role",
        "actor_ref",
        "old_values",
        "new_values",
        "created_at",
    }


def test_audit_log_out_has_from_attributes():
    assert AuditLogOut.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# PaginatedAuditLog
# ---------------------------------------------------------------------------


def test_paginated_audit_log_construction():
    row = FakeAuditLog()
    row.audit_id = 5
    row.entity_type = "Appeal"
    row.entity_id = "APL-000001"
    row.action = "INSERT"
    row.actor_role = "LEARNER"
    row.actor_ref = "LRN-001"
    row.old_values = None
    row.new_values = {"appeal_status": "SUBMITTED"}
    row.created_at = datetime(2026, 2, 1, 12, 0, 0)

    page = PaginatedAuditLog(
        items=[AuditLogOut.model_validate(row)],
        total_count=1,
        page=1,
        page_size=20,
    )
    assert page.total_count == 1
    assert page.page == 1
    assert page.page_size == 20
    assert len(page.items) == 1
    assert page.items[0].audit_id == 5


def test_paginated_audit_log_field_set():
    assert set(PaginatedAuditLog.model_fields.keys()) == {
        "items",
        "total_count",
        "page",
        "page_size",
    }
