"""Verification that audit report schemas build from ORM-like objects via from_attributes.

Validates: Requirements 20.1, 20.2, 20.3, 20.6
"""

from datetime import datetime

from backend.schemas.audit_reports import (
    AppealsWithoutReviewOut,
    ConflictReassignmentOut,
    EvidenceItemSummary,
    PostDecisionEvidenceOut,
)
from backend.schemas.cases import CaseEventOut


# ---------------------------------------------------------------------------
# Fake ORM-like objects
# ---------------------------------------------------------------------------


class FakeReviewer:
    pass


class FakeCaseReviewer:
    pass


class FakeEvidenceItem:
    pass


class FakeAppeal:
    pass


# ---------------------------------------------------------------------------
# EvidenceItemSummary (nested)
# ---------------------------------------------------------------------------


def test_evidence_item_summary_from_orm():
    e = FakeEvidenceItem()
    e.evidence_id = "EVD-000001"
    e.evidence_type = "DOCUMENT"
    e.description = "Late submission screenshot"
    e.added_at = datetime(2026, 1, 25, 8, 0, 0)
    e.is_material = False

    out = EvidenceItemSummary.model_validate(e)
    assert out.evidence_id == "EVD-000001"
    assert out.evidence_type == "DOCUMENT"
    assert out.description == "Late submission screenshot"
    assert out.added_at == datetime(2026, 1, 25, 8, 0, 0)
    assert out.is_material is False


def test_evidence_item_summary_field_set():
    assert set(EvidenceItemSummary.model_fields.keys()) == {
        "evidence_id",
        "evidence_type",
        "description",
        "added_at",
        "is_material",
    }


def test_evidence_item_summary_has_from_attributes():
    assert EvidenceItemSummary.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# ConflictReassignmentOut (20.1)
# ---------------------------------------------------------------------------


def test_conflict_reassignment_out_construction():
    out = ConflictReassignmentOut(
        assignment_id=42,
        case_id="INT-2026-000015",
        reviewer_id="REV-007",
        reviewer_name="Jane Doe",
        conflict_reason="Reviewer teaches this module",
        assigned_at=datetime(2026, 1, 10, 9, 0, 0),
        unassigned_at=datetime(2026, 1, 11, 14, 0, 0),
    )
    assert out.assignment_id == 42
    assert out.case_id == "INT-2026-000015"
    assert out.reviewer_id == "REV-007"
    assert out.reviewer_name == "Jane Doe"
    assert out.conflict_reason == "Reviewer teaches this module"
    assert out.assigned_at == datetime(2026, 1, 10, 9, 0, 0)
    assert out.unassigned_at == datetime(2026, 1, 11, 14, 0, 0)


def test_conflict_reassignment_out_nullable_fields():
    out = ConflictReassignmentOut(
        assignment_id=43,
        case_id="INT-2026-000020",
        reviewer_id="REV-003",
        reviewer_name="John Smith",
        conflict_reason=None,
        assigned_at=datetime(2026, 1, 12, 9, 0, 0),
        unassigned_at=None,
    )
    assert out.conflict_reason is None
    assert out.unassigned_at is None


def test_conflict_reassignment_out_field_set():
    assert set(ConflictReassignmentOut.model_fields.keys()) == {
        "assignment_id",
        "case_id",
        "reviewer_id",
        "reviewer_name",
        "conflict_reason",
        "assigned_at",
        "unassigned_at",
    }


def test_conflict_reassignment_out_has_from_attributes():
    assert ConflictReassignmentOut.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# PostDecisionEvidenceOut (20.2)
# ---------------------------------------------------------------------------


def test_post_decision_evidence_out_construction():
    out = PostDecisionEvidenceOut(
        case_id="INT-2026-000001",
        evidence=[
            EvidenceItemSummary(
                evidence_id="EVD-000001",
                evidence_type="DOCUMENT",
                description="Additional document after decision",
                added_at=datetime(2026, 2, 1, 10, 0, 0),
                is_material=False,
            ),
        ],
    )
    assert out.case_id == "INT-2026-000001"
    assert len(out.evidence) == 1
    assert out.evidence[0].evidence_id == "EVD-000001"
    assert out.evidence[0].is_material is False


def test_post_decision_evidence_out_empty():
    out = PostDecisionEvidenceOut(case_id="INT-2026-000002", evidence=[])
    assert out.case_id == "INT-2026-000002"
    assert out.evidence == []


def test_post_decision_evidence_out_field_set():
    assert set(PostDecisionEvidenceOut.model_fields.keys()) == {
        "case_id",
        "evidence",
    }


# ---------------------------------------------------------------------------
# AppealsWithoutReviewOut (20.3)
# ---------------------------------------------------------------------------


def test_appeals_without_review_out_construction():
    out = AppealsWithoutReviewOut(
        appeal_id="APL-000001",
        case_id="INT-2026-000010",
        appeal_status="UPHELD",
        submitted_at=datetime(2026, 2, 15, 12, 0, 0),
    )
    assert out.appeal_id == "APL-000001"
    assert out.case_id == "INT-2026-000010"
    assert out.appeal_status == "UPHELD"
    assert out.submitted_at == datetime(2026, 2, 15, 12, 0, 0)


def test_appeals_without_review_out_from_orm():
    a = FakeAppeal()
    a.appeal_id = "APL-000002"
    a.case_id = "INT-2026-000011"
    a.appeal_status = "OVERTURNED"
    a.submitted_at = datetime(2026, 3, 1, 9, 30, 0)

    out = AppealsWithoutReviewOut.model_validate(a)
    assert out.appeal_id == "APL-000002"
    assert out.case_id == "INT-2026-000011"
    assert out.appeal_status == "OVERTURNED"
    assert out.submitted_at == datetime(2026, 3, 1, 9, 30, 0)


def test_appeals_without_review_out_field_set():
    assert set(AppealsWithoutReviewOut.model_fields.keys()) == {
        "appeal_id",
        "case_id",
        "appeal_status",
        "submitted_at",
    }


def test_appeals_without_review_out_has_from_attributes():
    assert AppealsWithoutReviewOut.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# CaseEventOut re-export (20.6)
# ---------------------------------------------------------------------------


def test_case_event_out_is_importable():
    """CaseEventOut should be importable from audit_reports via cases."""
    assert CaseEventOut is not None
    assert set(CaseEventOut.model_fields.keys()) == {
        "event_id",
        "case_id",
        "event_type",
        "actor_role",
        "actor_ref",
        "previous_status",
        "new_status",
        "event_details",
        "occurred_at",
    }
