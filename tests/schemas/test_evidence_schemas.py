"""Verification that evidence schemas build from ORM-like objects via from_attributes.

Validates: Requirements 10.1, 10.2
"""

from datetime import datetime

from backend.schemas.evidence import (
    EvidenceItemCreate,
    EvidenceItemOut,
)


# ---------------------------------------------------------------------------
# Fake ORM-like objects
# ---------------------------------------------------------------------------


class FakeEvidenceItem:
    pass


# ---------------------------------------------------------------------------
# EvidenceItemCreate (request body — no from_attributes needed)
# ---------------------------------------------------------------------------


def test_evidence_item_create_minimal():
    payload = EvidenceItemCreate(
        evidence_type="SIMILARITY_MATCH",
        description="Text match report attached",
        added_by_role="REVIEWER",
        actor_role="REVIEWER",
    )
    assert payload.evidence_type == "SIMILARITY_MATCH"
    assert payload.description == "Text match report attached"
    assert payload.evidence_reference is None
    assert payload.added_by_ref is None
    assert payload.actor_role == "REVIEWER"


def test_evidence_item_create_full():
    payload = EvidenceItemCreate(
        evidence_type="DOCUMENT",
        description="Student statement document",
        evidence_reference="ref://docs/statement.pdf",
        added_by_role="LEARNER",
        added_by_ref="LRN-001",
        actor_role="INSTRUCTOR",
    )
    assert payload.evidence_reference == "ref://docs/statement.pdf"
    assert payload.added_by_role == "LEARNER"
    assert payload.added_by_ref == "LRN-001"
    assert payload.actor_role == "INSTRUCTOR"


def test_evidence_item_create_field_set():
    assert set(EvidenceItemCreate.model_fields.keys()) == {
        "evidence_type",
        "description",
        "evidence_reference",
        "added_by_role",
        "added_by_ref",
        "actor_role",
    }


def test_evidence_item_create_no_from_attributes():
    assert EvidenceItemCreate.model_config.get("from_attributes") is not True


# ---------------------------------------------------------------------------
# EvidenceItemOut (response — from_attributes)
# ---------------------------------------------------------------------------


def test_evidence_item_out_from_orm():
    e = FakeEvidenceItem()
    e.evidence_id = "EVD-000001"
    e.case_id = "INT-2026-000001"
    e.evidence_type = "SIMILARITY_MATCH"
    e.description = "Text match report attached"
    e.evidence_reference = "ref://docs/report.pdf"
    e.added_by_role = "REVIEWER"
    e.added_by_ref = "REV-001"
    e.added_at = datetime(2026, 1, 20, 10, 0, 0)
    e.is_material = True

    out = EvidenceItemOut.model_validate(e)
    assert out.evidence_id == "EVD-000001"
    assert out.case_id == "INT-2026-000001"
    assert out.evidence_type == "SIMILARITY_MATCH"
    assert out.description == "Text match report attached"
    assert out.evidence_reference == "ref://docs/report.pdf"
    assert out.added_by_role == "REVIEWER"
    assert out.added_by_ref == "REV-001"
    assert out.added_at == datetime(2026, 1, 20, 10, 0, 0)
    assert out.is_material is True


def test_evidence_item_out_nullable_fields():
    e = FakeEvidenceItem()
    e.evidence_id = "EVD-000002"
    e.case_id = "INT-2026-000002"
    e.evidence_type = "STUDENT_EXPLANATION"
    e.description = "Verbal explanation from learner"
    e.evidence_reference = None
    e.added_by_role = "LEARNER"
    e.added_by_ref = None
    e.added_at = datetime(2026, 1, 21, 14, 30, 0)
    e.is_material = False

    out = EvidenceItemOut.model_validate(e)
    assert out.evidence_reference is None
    assert out.added_by_ref is None
    assert out.is_material is False


def test_evidence_item_out_field_set():
    assert set(EvidenceItemOut.model_fields.keys()) == {
        "evidence_id",
        "case_id",
        "evidence_type",
        "description",
        "evidence_reference",
        "added_by_role",
        "added_by_ref",
        "added_at",
        "is_material",
    }


def test_evidence_item_out_has_from_attributes():
    assert EvidenceItemOut.model_config.get("from_attributes") is True
