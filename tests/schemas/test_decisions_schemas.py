"""Verification that decision schemas build from ORM-like objects via from_attributes.

Validates: Requirements 11.1, 11.2, 11.6
"""

from datetime import datetime

from backend.schemas.decisions import (
    DecisionCreate,
    DecisionOut,
)


# ---------------------------------------------------------------------------
# Fake ORM-like objects
# ---------------------------------------------------------------------------


class FakeDecision:
    pass


# ---------------------------------------------------------------------------
# DecisionCreate (request body — no from_attributes needed)
# ---------------------------------------------------------------------------


def test_decision_create_minimal():
    payload = DecisionCreate(
        reviewer_id="REV-001",
        decision_outcome="VIOLATION",
        rationale="Substantial text match confirmed across multiple paragraphs",
        actor_role="REVIEWER",
    )
    assert payload.reviewer_id == "REV-001"
    assert payload.decision_outcome == "VIOLATION"
    assert payload.previous_decision_id is None
    assert payload.evidence_ids == []
    assert payload.actor_role == "REVIEWER"


def test_decision_create_with_previous_and_evidence():
    payload = DecisionCreate(
        reviewer_id="REV-002",
        decision_outcome="INCONCLUSIVE",
        rationale="Insufficient evidence to determine violation",
        previous_decision_id=5,
        evidence_ids=["EVD-000001", "EVD-000002", "EVD-000003"],
        actor_role="ACADEMIC_ADMIN",
    )
    assert payload.previous_decision_id == 5
    assert len(payload.evidence_ids) == 3
    assert "EVD-000001" in payload.evidence_ids


def test_decision_create_field_set():
    assert set(DecisionCreate.model_fields.keys()) == {
        "reviewer_id",
        "decision_outcome",
        "rationale",
        "previous_decision_id",
        "evidence_ids",
        "actor_role",
    }


def test_decision_create_no_from_attributes():
    assert DecisionCreate.model_config.get("from_attributes") is not True


# ---------------------------------------------------------------------------
# DecisionOut (response — from_attributes)
# ---------------------------------------------------------------------------


def test_decision_out_from_orm():
    d = FakeDecision()
    d.decision_id = 1
    d.case_id = "INT-2026-000001"
    d.reviewer_id = "REV-001"
    d.previous_decision_id = None
    d.decision_outcome = "VIOLATION"
    d.rationale = "Substantial text match confirmed"
    d.decided_at = datetime(2026, 2, 1, 14, 0, 0)
    d.is_final = True

    out = DecisionOut.model_validate(d)
    assert out.decision_id == 1
    assert out.case_id == "INT-2026-000001"
    assert out.reviewer_id == "REV-001"
    assert out.previous_decision_id is None
    assert out.decision_outcome == "VIOLATION"
    assert out.rationale == "Substantial text match confirmed"
    assert out.decided_at == datetime(2026, 2, 1, 14, 0, 0)
    assert out.is_final is True


def test_decision_out_with_previous_decision():
    d = FakeDecision()
    d.decision_id = 2
    d.case_id = "INT-2026-000002"
    d.reviewer_id = "REV-003"
    d.previous_decision_id = 1
    d.decision_outcome = "NO_VIOLATION"
    d.rationale = "Original decision overturned on review"
    d.decided_at = datetime(2026, 2, 5, 10, 0, 0)
    d.is_final = False

    out = DecisionOut.model_validate(d)
    assert out.previous_decision_id == 1
    assert out.decision_outcome == "NO_VIOLATION"
    assert out.is_final is False


def test_decision_out_field_set():
    assert set(DecisionOut.model_fields.keys()) == {
        "decision_id",
        "case_id",
        "reviewer_id",
        "previous_decision_id",
        "decision_outcome",
        "rationale",
        "decided_at",
        "is_final",
    }


def test_decision_out_has_from_attributes():
    assert DecisionOut.model_config.get("from_attributes") is True
