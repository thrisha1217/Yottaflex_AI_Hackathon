"""Verification that appeal schemas build from ORM-like objects via from_attributes.

Validates: Requirements 12.1, 12.3
"""

from datetime import datetime

from backend.schemas.appeals import (
    AppealCreate,
    AppealOut,
    AppealReviewCreate,
    AppealReviewOut,
)


# ---------------------------------------------------------------------------
# Fake ORM-like objects
# ---------------------------------------------------------------------------


class FakeAppeal:
    pass


class FakeAppealReview:
    pass


# ---------------------------------------------------------------------------
# AppealCreate (request body — no from_attributes needed)
# ---------------------------------------------------------------------------


def test_appeal_create_minimal():
    payload = AppealCreate(
        learner_id="LRN-001",
        reason="I believe the similarity match is a false positive due to proper citation",
        actor_role="LEARNER",
    )
    assert payload.learner_id == "LRN-001"
    assert payload.reason.startswith("I believe")
    assert payload.actor_role == "LEARNER"


def test_appeal_create_field_set():
    assert set(AppealCreate.model_fields.keys()) == {
        "learner_id",
        "reason",
        "actor_role",
    }


def test_appeal_create_no_from_attributes():
    assert AppealCreate.model_config.get("from_attributes") is not True


# ---------------------------------------------------------------------------
# AppealOut (response — from_attributes)
# ---------------------------------------------------------------------------


def test_appeal_out_from_orm():
    a = FakeAppeal()
    a.appeal_id = "APL-000001"
    a.case_id = "INT-2026-000001"
    a.learner_id = "LRN-001"
    a.appeal_no = 1
    a.reason = "False positive match due to proper citation"
    a.submitted_at = datetime(2026, 3, 1, 12, 0, 0)
    a.appeal_status = "SUBMITTED"
    a.resolved_at = None

    out = AppealOut.model_validate(a)
    assert out.appeal_id == "APL-000001"
    assert out.case_id == "INT-2026-000001"
    assert out.learner_id == "LRN-001"
    assert out.appeal_no == 1
    assert out.reason == "False positive match due to proper citation"
    assert out.submitted_at == datetime(2026, 3, 1, 12, 0, 0)
    assert out.appeal_status == "SUBMITTED"
    assert out.resolved_at is None


def test_appeal_out_resolved():
    a = FakeAppeal()
    a.appeal_id = "APL-000002"
    a.case_id = "INT-2026-000002"
    a.learner_id = "LRN-005"
    a.appeal_no = 1
    a.reason = "Decision should be overturned"
    a.submitted_at = datetime(2026, 3, 2, 9, 0, 0)
    a.appeal_status = "OVERTURNED"
    a.resolved_at = datetime(2026, 3, 10, 15, 30, 0)

    out = AppealOut.model_validate(a)
    assert out.appeal_status == "OVERTURNED"
    assert out.resolved_at == datetime(2026, 3, 10, 15, 30, 0)


def test_appeal_out_field_set():
    assert set(AppealOut.model_fields.keys()) == {
        "appeal_id",
        "case_id",
        "learner_id",
        "appeal_no",
        "reason",
        "submitted_at",
        "appeal_status",
        "resolved_at",
    }


def test_appeal_out_has_from_attributes():
    assert AppealOut.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# AppealReviewCreate (request body — no from_attributes needed)
# ---------------------------------------------------------------------------


def test_appeal_review_create_minimal():
    payload = AppealReviewCreate(
        reviewer_id="REV-010",
        outcome="UPHELD",
        rationale="Original decision stands after independent review",
        independence_verified=True,
        actor_role="ACADEMIC_ADMIN",
    )
    assert payload.reviewer_id == "REV-010"
    assert payload.outcome == "UPHELD"
    assert payload.independence_verified is True
    assert payload.actor_role == "ACADEMIC_ADMIN"


def test_appeal_review_create_with_overturned():
    payload = AppealReviewCreate(
        reviewer_id="REV-015",
        outcome="OVERTURNED",
        rationale="New evidence shows proper citation",
        independence_verified=True,
        actor_role="REVIEWER",
    )
    assert payload.outcome == "OVERTURNED"
    assert payload.independence_verified is True


def test_appeal_review_create_field_set():
    assert set(AppealReviewCreate.model_fields.keys()) == {
        "reviewer_id",
        "outcome",
        "rationale",
        "independence_verified",
        "actor_role",
    }


def test_appeal_review_create_no_from_attributes():
    assert AppealReviewCreate.model_config.get("from_attributes") is not True


# ---------------------------------------------------------------------------
# AppealReviewOut (response — from_attributes)
# ---------------------------------------------------------------------------


def test_appeal_review_out_from_orm():
    ar = FakeAppealReview()
    ar.review_id = 1
    ar.appeal_id = "APL-000001"
    ar.reviewer_id = "REV-010"
    ar.outcome = "UPHELD"
    ar.rationale = "Original decision stands after independent review"
    ar.independence_verified = True
    ar.reviewed_at = datetime(2026, 3, 10, 15, 0, 0)

    out = AppealReviewOut.model_validate(ar)
    assert out.review_id == 1
    assert out.appeal_id == "APL-000001"
    assert out.reviewer_id == "REV-010"
    assert out.outcome == "UPHELD"
    assert out.rationale == "Original decision stands after independent review"
    assert out.independence_verified is True
    assert out.reviewed_at == datetime(2026, 3, 10, 15, 0, 0)


def test_appeal_review_out_remanded():
    ar = FakeAppealReview()
    ar.review_id = 2
    ar.appeal_id = "APL-000003"
    ar.reviewer_id = "REV-012"
    ar.outcome = "REMANDED"
    ar.rationale = "Case requires further investigation"
    ar.independence_verified = True
    ar.reviewed_at = datetime(2026, 3, 12, 10, 0, 0)

    out = AppealReviewOut.model_validate(ar)
    assert out.outcome == "REMANDED"
    assert out.independence_verified is True


def test_appeal_review_out_field_set():
    assert set(AppealReviewOut.model_fields.keys()) == {
        "review_id",
        "appeal_id",
        "reviewer_id",
        "outcome",
        "rationale",
        "independence_verified",
        "reviewed_at",
    }


def test_appeal_review_out_has_from_attributes():
    assert AppealReviewOut.model_config.get("from_attributes") is True
