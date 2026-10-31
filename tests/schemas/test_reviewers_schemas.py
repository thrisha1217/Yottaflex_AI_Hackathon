"""Verification that reviewer schemas build from ORM-like objects via from_attributes.

Validates: Requirements 9.1, 9.2, 9.6
"""

from datetime import datetime

from backend.schemas.reviewers import (
    CaseReviewerCreate,
    CaseReviewerOut,
    ConflictUpdate,
    PaginatedReviewers,
    ReviewerOut,
)


# ---------------------------------------------------------------------------
# Fake ORM-like objects
# ---------------------------------------------------------------------------


class FakeReviewer:
    pass


class FakeCaseReviewer:
    pass


# ---------------------------------------------------------------------------
# ReviewerOut (response — from_attributes)
# ---------------------------------------------------------------------------


def test_reviewer_out_from_orm():
    r = FakeReviewer()
    r.reviewer_id = "REV-001"
    r.full_name = "Jane Doe"
    r.email = "jane.doe@uni.edu"
    r.reviewer_role = "INSTRUCTOR"
    r.status = "ACTIVE"
    r.created_at = datetime(2026, 1, 1, 0, 0, 0)

    ro = ReviewerOut.model_validate(r)
    assert ro.reviewer_id == "REV-001"
    assert ro.full_name == "Jane Doe"
    assert ro.email == "jane.doe@uni.edu"
    assert ro.reviewer_role == "INSTRUCTOR"
    assert ro.status == "ACTIVE"
    assert ro.created_at == datetime(2026, 1, 1, 0, 0, 0)


def test_reviewer_out_field_set():
    assert set(ReviewerOut.model_fields.keys()) == {
        "reviewer_id",
        "full_name",
        "email",
        "reviewer_role",
        "status",
        "created_at",
    }


def test_reviewer_out_has_from_attributes():
    assert ReviewerOut.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# CaseReviewerOut (response — from_attributes)
# ---------------------------------------------------------------------------


def test_case_reviewer_out_from_orm():
    cr = FakeCaseReviewer()
    cr.assignment_id = 5
    cr.case_id = "INT-2026-000001"
    cr.reviewer_id = "REV-002"
    cr.assignment_role = "PRIMARY"
    cr.assigned_at = datetime(2026, 1, 16, 9, 0, 0)
    cr.unassigned_at = None
    cr.conflict_status = "PENDING"
    cr.conflict_reason = None

    out = CaseReviewerOut.model_validate(cr)
    assert out.assignment_id == 5
    assert out.case_id == "INT-2026-000001"
    assert out.reviewer_id == "REV-002"
    assert out.assignment_role == "PRIMARY"
    assert out.assigned_at == datetime(2026, 1, 16, 9, 0, 0)
    assert out.unassigned_at is None
    assert out.conflict_status == "PENDING"
    assert out.conflict_reason is None


def test_case_reviewer_out_with_conflict():
    cr = FakeCaseReviewer()
    cr.assignment_id = 6
    cr.case_id = "INT-2026-000002"
    cr.reviewer_id = "REV-003"
    cr.assignment_role = "SECONDARY"
    cr.assigned_at = datetime(2026, 1, 16, 9, 0, 0)
    cr.unassigned_at = datetime(2026, 1, 17, 12, 0, 0)
    cr.conflict_status = "CONFLICT"
    cr.conflict_reason = "Prior relationship with student"

    out = CaseReviewerOut.model_validate(cr)
    assert out.conflict_status == "CONFLICT"
    assert out.unassigned_at == datetime(2026, 1, 17, 12, 0, 0)
    assert out.conflict_reason == "Prior relationship with student"


def test_case_reviewer_out_field_set():
    assert set(CaseReviewerOut.model_fields.keys()) == {
        "assignment_id",
        "case_id",
        "reviewer_id",
        "assignment_role",
        "assigned_at",
        "unassigned_at",
        "conflict_status",
        "conflict_reason",
    }


def test_case_reviewer_out_has_from_attributes():
    assert CaseReviewerOut.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# CaseReviewerCreate (request body — no from_attributes)
# ---------------------------------------------------------------------------


def test_case_reviewer_create_minimal():
    payload = CaseReviewerCreate(
        reviewer_id="REV-001", assignment_role="PRIMARY", actor_role="ACADEMIC_ADMIN"
    )
    assert payload.reviewer_id == "REV-001"
    assert payload.assignment_role == "PRIMARY"
    assert payload.actor_role == "ACADEMIC_ADMIN"


def test_case_reviewer_create_field_set():
    assert set(CaseReviewerCreate.model_fields.keys()) == {
        "reviewer_id",
        "assignment_role",
        "actor_role",
    }


def test_case_reviewer_create_no_from_attributes():
    assert CaseReviewerCreate.model_config.get("from_attributes") is not True


# ---------------------------------------------------------------------------
# ConflictUpdate (request body — no from_attributes)
# ---------------------------------------------------------------------------


def test_conflict_update_minimal():
    payload = ConflictUpdate(
        conflict_status="CONFLICT", actor_role="REVIEWER"
    )
    assert payload.conflict_status == "CONFLICT"
    assert payload.actor_role == "REVIEWER"
    assert payload.conflict_reason is None
    assert payload.actor_ref is None


def test_conflict_update_with_reason_and_ref():
    payload = ConflictUpdate(
        conflict_status="CONFLICT",
        conflict_reason="Personal relationship",
        actor_role="ACADEMIC_ADMIN",
        actor_ref="REV-001",
    )
    assert payload.conflict_reason == "Personal relationship"
    assert payload.actor_ref == "REV-001"


def test_conflict_update_field_set():
    assert set(ConflictUpdate.model_fields.keys()) == {
        "conflict_status",
        "conflict_reason",
        "actor_role",
        "actor_ref",
    }


# ---------------------------------------------------------------------------
# PaginatedReviewers
# ---------------------------------------------------------------------------


def test_paginated_reviewers_envelope():
    r = FakeReviewer()
    r.reviewer_id = "REV-001"
    r.full_name = "Jane Doe"
    r.email = "jane@uni.edu"
    r.reviewer_role = "INSTRUCTOR"
    r.status = "ACTIVE"
    r.created_at = datetime(2026, 1, 1)

    items = [ReviewerOut.model_validate(r)]
    p = PaginatedReviewers(items=items, total_count=30, page=1, page_size=20)

    assert p.total_count == 30
    assert p.page == 1
    assert p.page_size == 20
    assert len(p.items) == 1
    assert isinstance(p.items[0], ReviewerOut)
    assert set(PaginatedReviewers.model_fields.keys()) == {
        "items",
        "total_count",
        "page",
        "page_size",
    }


def test_paginated_reviewers_empty_page():
    p = PaginatedReviewers(items=[], total_count=0, page=1, page_size=20)
    assert p.items == []
    assert p.total_count == 0
