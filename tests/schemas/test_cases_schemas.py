"""Verification that case schemas build from ORM-like objects via from_attributes.

Validates: Requirements 8.1, 8.2, 8.3
"""

from datetime import datetime

from backend.schemas.cases import (
    CaseDetail,
    CaseEventOut,
    CaseReviewerSummary,
    CaseStatus,
    CaseStatusUpdate,
    CaseSummary,
    DecisionSummary,
    PaginatedCases,
    Priority,
)
from backend.schemas.submissions import SimilarityReportSummary


# ---------------------------------------------------------------------------
# Fake ORM-like objects
# ---------------------------------------------------------------------------


class FakeReport:
    pass


class FakeReviewer:
    pass


class FakeEvent:
    pass


class FakeDecision:
    pass


class FakeCase:
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


def test_case_status_values():
    assert CaseStatus.OPEN == "OPEN"
    assert CaseStatus.UNDER_REVIEW == "UNDER_REVIEW"
    assert CaseStatus.AWAITING_INFORMATION == "AWAITING_INFORMATION"
    assert CaseStatus.DECIDED == "DECIDED"
    assert CaseStatus.APPEAL_PENDING == "APPEAL_PENDING"
    assert CaseStatus.CLOSED == "CLOSED"


def test_priority_values():
    assert Priority.LOW == "LOW"
    assert Priority.MEDIUM == "MEDIUM"
    assert Priority.HIGH == "HIGH"


# ---------------------------------------------------------------------------
# CaseStatusUpdate (request body — no from_attributes needed)
# ---------------------------------------------------------------------------


def test_case_status_update_minimal():
    payload = CaseStatusUpdate(case_status=CaseStatus.UNDER_REVIEW, actor_role="REVIEWER")
    assert payload.case_status == CaseStatus.UNDER_REVIEW
    assert payload.actor_role == "REVIEWER"
    assert payload.actor_ref is None


def test_case_status_update_with_actor_ref():
    payload = CaseStatusUpdate(
        case_status=CaseStatus.CLOSED,
        actor_role="ACADEMIC_ADMIN",
        actor_ref="REV-001",
    )
    assert payload.actor_ref == "REV-001"


# ---------------------------------------------------------------------------
# CaseSummary (list item — from_attributes)
# ---------------------------------------------------------------------------


def test_case_summary_from_orm():
    c = FakeCase()
    c.case_id = "INT-2026-000001"
    c.case_status = "OPEN"
    c.priority = "MEDIUM"
    c.opened_at = datetime(2026, 1, 15, 10, 0, 0)
    c.closed_at = None
    c.has_conflict = False

    cs = CaseSummary.model_validate(c)
    assert cs.case_id == "INT-2026-000001"
    assert cs.case_status == CaseStatus.OPEN
    assert cs.priority == "MEDIUM"
    assert cs.opened_at == datetime(2026, 1, 15, 10, 0, 0)
    assert cs.closed_at is None
    assert cs.has_conflict is False


def test_case_summary_with_conflict():
    c = FakeCase()
    c.case_id = "INT-2026-000002"
    c.case_status = "UNDER_REVIEW"
    c.priority = "HIGH"
    c.opened_at = datetime(2026, 2, 1, 9, 0, 0)
    c.closed_at = None
    c.has_conflict = True

    cs = CaseSummary.model_validate(c)
    assert cs.has_conflict is True


def test_case_summary_closed():
    c = FakeCase()
    c.case_id = "INT-2026-000003"
    c.case_status = "CLOSED"
    c.priority = "LOW"
    c.opened_at = datetime(2026, 1, 1, 0, 0, 0)
    c.closed_at = datetime(2026, 3, 1, 12, 0, 0)
    c.has_conflict = False

    cs = CaseSummary.model_validate(c)
    assert cs.closed_at == datetime(2026, 3, 1, 12, 0, 0)
    assert cs.case_status == CaseStatus.CLOSED


# ---------------------------------------------------------------------------
# Nested schemas (CaseEventOut, CaseReviewerSummary, DecisionSummary)
# ---------------------------------------------------------------------------


def test_case_event_out_from_orm():
    e = FakeEvent()
    e.event_id = 1
    e.case_id = "INT-2026-000001"
    e.event_type = "STATUS_CHANGED"
    e.actor_role = "REVIEWER"
    e.actor_ref = "REV-001"
    e.previous_status = "OPEN"
    e.new_status = "UNDER_REVIEW"
    e.event_details = {"note": "escalated"}
    e.occurred_at = datetime(2026, 1, 16, 8, 30, 0)

    ev = CaseEventOut.model_validate(e)
    assert ev.event_id == 1
    assert ev.event_type == "STATUS_CHANGED"
    assert ev.actor_ref == "REV-001"
    assert ev.previous_status == "OPEN"
    assert ev.new_status == "UNDER_REVIEW"
    assert ev.event_details == {"note": "escalated"}
    assert ev.occurred_at == datetime(2026, 1, 16, 8, 30, 0)


def test_case_event_out_nullable_fields():
    e = FakeEvent()
    e.event_id = 2
    e.case_id = "INT-2026-000001"
    e.event_type = "CASE_CREATED"
    e.actor_role = "SYSTEM"
    e.actor_ref = None
    e.previous_status = None
    e.new_status = None
    e.event_details = None
    e.occurred_at = datetime(2026, 1, 15, 10, 0, 0)

    ev = CaseEventOut.model_validate(e)
    assert ev.actor_ref is None
    assert ev.previous_status is None
    assert ev.new_status is None
    assert ev.event_details is None


def test_case_reviewer_summary_from_orm():
    r = FakeReviewer()
    r.assignment_id = 10
    r.case_id = "INT-2026-000001"
    r.reviewer_id = "REV-001"
    r.assignment_role = "PRIMARY"
    r.assigned_at = datetime(2026, 1, 16, 9, 0, 0)
    r.unassigned_at = None
    r.conflict_status = "CLEARED"
    r.conflict_reason = None

    rv = CaseReviewerSummary.model_validate(r)
    assert rv.assignment_id == 10
    assert rv.reviewer_id == "REV-001"
    assert rv.assignment_role == "PRIMARY"
    assert rv.conflict_status == "CLEARED"
    assert rv.unassigned_at is None
    assert rv.conflict_reason is None


def test_case_reviewer_summary_with_conflict():
    r = FakeReviewer()
    r.assignment_id = 11
    r.case_id = "INT-2026-000001"
    r.reviewer_id = "REV-005"
    r.assignment_role = "SECONDARY"
    r.assigned_at = datetime(2026, 1, 16, 9, 0, 0)
    r.unassigned_at = datetime(2026, 1, 17, 12, 0, 0)
    r.conflict_status = "CONFLICT"
    r.conflict_reason = "Prior relationship with student"

    rv = CaseReviewerSummary.model_validate(r)
    assert rv.conflict_status == "CONFLICT"
    assert rv.unassigned_at == datetime(2026, 1, 17, 12, 0, 0)
    assert rv.conflict_reason == "Prior relationship with student"


def test_decision_summary_from_orm():
    d = FakeDecision()
    d.decision_id = 1
    d.case_id = "INT-2026-000001"
    d.decision_outcome = "VIOLATION"
    d.rationale = "Substantial text match confirmed"
    d.decided_at = datetime(2026, 2, 1, 14, 0, 0)
    d.is_final = True

    ds = DecisionSummary.model_validate(d)
    assert ds.decision_id == 1
    assert ds.case_id == "INT-2026-000001"
    assert ds.decision_outcome == "VIOLATION"
    assert ds.rationale == "Substantial text match confirmed"
    assert ds.decided_at == datetime(2026, 2, 1, 14, 0, 0)
    assert ds.is_final is True


# ---------------------------------------------------------------------------
# CaseDetail (full record)
# ---------------------------------------------------------------------------


def _make_report():
    r = FakeReport()
    r.report_id = "SIM-x-01"
    r.submission_id = "SUB-2026-000001"
    r.similarity_score = 78.50
    r.review_required = True
    r.report_status = "REVIEW_REQUIRED"
    r.generated_at = datetime(2026, 1, 10, 6, 0, 0)
    return r


def _make_reviewer():
    r = FakeReviewer()
    r.assignment_id = 1
    r.case_id = "INT-2026-000001"
    r.reviewer_id = "REV-001"
    r.assignment_role = "PRIMARY"
    r.assigned_at = datetime(2026, 1, 16, 9, 0, 0)
    r.unassigned_at = None
    r.conflict_status = "CLEARED"
    r.conflict_reason = None
    return r


def _make_decision():
    d = FakeDecision()
    d.decision_id = 1
    d.case_id = "INT-2026-000001"
    d.decision_outcome = "VIOLATION"
    d.rationale = "Confirmed plagiarism"
    d.decided_at = datetime(2026, 2, 1, 14, 0, 0)
    d.is_final = True
    return d


def _make_event():
    e = FakeEvent()
    e.event_id = 1
    e.case_id = "INT-2026-000001"
    e.event_type = "CASE_CREATED"
    e.actor_role = "SYSTEM"
    e.actor_ref = None
    e.previous_status = None
    e.new_status = None
    e.event_details = None
    e.occurred_at = datetime(2026, 1, 15, 10, 0, 0)
    return e


def _make_case():
    c = FakeCase()
    c.case_id = "INT-2026-000001"
    c.case_status = "UNDER_REVIEW"
    c.priority = "HIGH"
    c.opened_at = datetime(2026, 1, 15, 10, 0, 0)
    c.closed_at = None
    c.has_conflict = False
    c.report_summary = _make_report()
    c.reviewers = [_make_reviewer()]
    c.decision_summary = _make_decision()
    c.events = [_make_event()]
    return c


def test_case_detail_full_from_orm():
    c = _make_case()

    cd = CaseDetail.model_validate(c)
    assert cd.case_id == "INT-2026-000001"
    assert cd.case_status == CaseStatus.UNDER_REVIEW
    assert cd.priority == "HIGH"
    assert cd.has_conflict is False

    # report_summary is a SimilarityReportSummary built from the report object
    assert isinstance(cd.report_summary, SimilarityReportSummary)
    assert cd.report_summary.report_id == "SIM-x-01"
    assert cd.report_summary.similarity_score == 78.50

    # reviewers
    assert len(cd.reviewers) == 1
    assert isinstance(cd.reviewers[0], CaseReviewerSummary)
    assert cd.reviewers[0].reviewer_id == "REV-001"

    # decision_summary
    assert cd.decision_summary is not None
    assert isinstance(cd.decision_summary, DecisionSummary)
    assert cd.decision_summary.decision_outcome == "VIOLATION"
    assert cd.decision_summary.is_final is True

    # events
    assert len(cd.events) == 1
    assert isinstance(cd.events[0], CaseEventOut)
    assert cd.events[0].event_type == "CASE_CREATED"


def test_case_detail_without_decision():
    c = _make_case()
    c.decision_summary = None

    cd = CaseDetail.model_validate(c)
    assert cd.decision_summary is None


def test_case_detail_empty_nested_lists():
    c = _make_case()
    c.reviewers = []
    c.events = []

    cd = CaseDetail.model_validate(c)
    assert cd.reviewers == []
    assert cd.events == []


def test_case_detail_inherits_summary_fields():
    """CaseDetail extends CaseSummary, so it must have all summary fields."""
    summary_fields = set(CaseSummary.model_fields.keys())
    detail_fields = set(CaseDetail.model_fields.keys())
    assert summary_fields.issubset(detail_fields)
    # Extra fields on detail
    assert {"report_summary", "reviewers", "decision_summary", "events"}.issubset(
        detail_fields - summary_fields
    )


# ---------------------------------------------------------------------------
# PaginatedCases
# ---------------------------------------------------------------------------


def test_paginated_cases_envelope():
    c = FakeCase()
    c.case_id = "INT-2026-000001"
    c.case_status = "OPEN"
    c.priority = "MEDIUM"
    c.opened_at = datetime(2026, 1, 15, 10, 0, 0)
    c.closed_at = None
    c.has_conflict = False

    items = [CaseSummary.model_validate(c)]
    p = PaginatedCases(items=items, total_count=300, page=1, page_size=20)

    assert p.total_count == 300
    assert p.page == 1
    assert p.page_size == 20
    assert len(p.items) == 1
    assert isinstance(p.items[0], CaseSummary)
    assert p.items[0].case_id == "INT-2026-000001"
    assert set(PaginatedCases.model_fields.keys()) == {
        "items",
        "total_count",
        "page",
        "page_size",
    }


def test_paginated_cases_empty_page():
    p = PaginatedCases(items=[], total_count=0, page=1, page_size=20)
    assert p.items == []
    assert p.total_count == 0
