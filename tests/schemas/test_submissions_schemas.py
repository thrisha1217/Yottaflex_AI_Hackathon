"""Verification that submission schemas build from ORM-like objects via from_attributes."""

from datetime import datetime
from decimal import Decimal

from backend.schemas.submissions import (
    PaginatedSubmissions,
    RuleSummary,
    SimilarityReportDetail,
    SimilarityReportSummary,
    SubmissionDetail,
    SubmissionSummary,
)


class FakeRule:
    pass


class FakeReport:
    pass


class FakeSubmission:
    pass


def test_submission_detail_with_report():
    r = FakeReport()
    r.report_id = "SIM-x-01"
    r.submission_id = "SUB-1"
    r.similarity_score = Decimal("78.50")
    r.review_required = True
    r.report_status = "REVIEW_REQUIRED"
    r.generated_at = datetime(2026, 1, 2, 3, 0, 0)

    s = FakeSubmission()
    s.submission_id = "SUB-2026-000001"
    s.learner_id = "LRN-001"
    s.assessment_id = "ASM-001"
    s.attempt_no = 1
    s.submitted_at = datetime(2026, 1, 1, 12, 0, 0)
    s.status = "SUBMITTED"
    s.similarity_score = None
    s.review_required = None
    s.content_reference = "ref"
    s.content_hash = "abc"
    s.report = r

    sd = SubmissionDetail.model_validate(s)
    assert sd.submission_id == "SUB-2026-000001"
    assert sd.report is not None
    # Decimal coerced to float
    assert sd.report.similarity_score == 78.50
    assert isinstance(sd.report.similarity_score, float)
    assert sd.report.review_required is True
    assert sd.content_hash == "abc"
    assert isinstance(sd.report, SimilarityReportSummary)


def test_submission_without_report():
    s = FakeSubmission()
    s.submission_id = "SUB-2"
    s.learner_id = "LRN-002"
    s.assessment_id = "ASM-002"
    s.attempt_no = 2
    s.submitted_at = datetime(2026, 2, 1, 9, 0, 0)
    s.status = "LATE"
    s.similarity_score = None
    s.review_required = None
    s.content_reference = None
    s.content_hash = None
    s.report = None

    sd = SubmissionDetail.model_validate(s)
    assert sd.report is None
    assert sd.similarity_score is None
    assert sd.review_required is None


def test_similarity_report_detail_with_rule():
    rule = FakeRule()
    rule.rule_id = "RULE-003"
    rule.rule_name = "Review Threshold"
    rule.action_type = "REVIEW"

    r = FakeReport()
    r.report_id = "SIM-x-02"
    r.submission_id = "SUB-2"
    r.similarity_score = Decimal("88.00")
    r.review_required = True
    r.report_status = "REVIEW_REQUIRED"
    r.generated_at = datetime(2026, 1, 2, 3, 0, 0)
    r.report_no = 1
    r.matched_source_count = 3
    r.rule_id = "RULE-003"
    r.rule = rule

    rd = SimilarityReportDetail.model_validate(r)
    assert rd.rule is not None
    assert isinstance(rd.rule, RuleSummary)
    assert rd.rule.rule_name == "Review Threshold"
    assert rd.report_no == 1
    assert rd.matched_source_count == 3
    assert rd.rule_id == "RULE-003"
    assert rd.similarity_score == 88.00


def test_similarity_report_detail_without_rule():
    r = FakeReport()
    r.report_id = "SIM-x-03"
    r.submission_id = "SUB-3"
    r.similarity_score = Decimal("20.00")
    r.review_required = False
    r.report_status = "NO_REVIEW"
    r.generated_at = datetime(2026, 1, 2, 3, 0, 0)
    r.report_no = 1
    r.matched_source_count = 0
    r.rule_id = None
    r.rule = None

    rd = SimilarityReportDetail.model_validate(r)
    assert rd.rule is None
    assert rd.rule_id is None


def test_paginated_envelope():
    items = [
        SubmissionSummary(
            submission_id="SUB-1",
            learner_id="LRN-001",
            assessment_id="ASM-001",
            attempt_no=1,
            submitted_at=datetime(2026, 1, 1),
            status="SUBMITTED",
        ),
    ]
    p = PaginatedSubmissions(
        items=items, total_count=100, page=1, page_size=20
    )
    assert p.total_count == 100
    assert p.page == 1
    assert p.page_size == 20
    assert len(p.items) == 1
    assert set(PaginatedSubmissions.model_fields.keys()) == {
        "items",
        "total_count",
        "page",
        "page_size",
    }
