"""
tests/services/test_submission_service.py

Verification tests for the submission query functions in
backend/services/case_service.py.

Uses an in-memory SQLite database so no MySQL instance is needed. Only the
tables relevant to submission/similarity-report queries are created
(Learner, Assessment, IntegrityRule, Submission, SimilarityReport).
SQLite does not enforce FK constraints by default, so the parent rows are
inserted for realism.

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

import os

# Point the app's DATABASE_URL at a throwaway SQLite file BEFORE importing any
# backend module. The engine created in backend.database is lazy and never
# connects, so the import succeeds without the mysql-connector dependency.
os.environ.setdefault("DATABASE_URL", "sqlite:///./_submission_test_unused.db")

from datetime import date, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database import Base
from backend.models.assessment import Assessment
from backend.models.integrity_rule import IntegrityRule
from backend.models.learner import Learner
from backend.models.similarity_report import SimilarityReport
from backend.models.submission import Submission
from backend.schemas.submissions import (
    PaginatedSubmissions,
    SimilarityReportDetail,
    SubmissionDetail,
)
from backend.services.case_service import (
    get_similarity_report,
    get_submission_detail,
    get_submissions,
)


# ── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def db_session():
    """
    Module-scoped in-memory SQLite session with test data pre-loaded.

    The data set:
      * 1 Learner, 1 Assessment, 1 IntegrityRule
      * 5 Submissions (SUB-2026-000001 … 000005)
      * SimilarityReports for 4 of them:
          SUB-1  → flagged  (review_required=True,  score=85.50, has rule)
          SUB-2  → flagged  (review_required=True,  score=92.00, has rule)
          SUB-3  → unflagged(review_required=False, score=45.00, has rule)
          SUB-5  → unflagged(review_required=False, score=30.00, NO rule)
      * SUB-4 has no report at all.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)

    Base.metadata.create_all(
        engine,
        tables=[
            Learner.__table__,
            Assessment.__table__,
            IntegrityRule.__table__,
            Submission.__table__,
            SimilarityReport.__table__,
        ],
    )

    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestSession()

    # ── Reference data ───────────────────────────────────────────────────
    session.add(
        Learner(
            learner_id="LRN-001",
            full_name="Test Learner",
            email="learner@test.edu",
            program="Computer Science",
            year_of_study=2,
            status="ACTIVE",
            created_at=datetime(2026, 1, 1),
        )
    )

    session.add(
        Assessment(
            assessment_id="ASM-001",
            title="Research Essay",
            course_code="CS101",
            assessment_type="ASSIGNMENT",
            due_at=datetime(2026, 3, 1),
            status="ACTIVE",
            created_at=datetime(2026, 1, 1),
        )
    )

    session.add(
        IntegrityRule(
            rule_id="RULE-001",
            rule_name="Review Threshold",
            min_similarity=71.00,
            max_similarity=85.00,
            action_type="REVIEW",
            priority=3,
            effective_from=date(2026, 1, 1),
            is_active=True,
        )
    )

    # ── Submissions ──────────────────────────────────────────────────────
    submitted_at = datetime(2026, 2, 15, 10, 0, 0)
    for i in range(1, 6):
        session.add(
            Submission(
                submission_id=f"SUB-2026-{i:06d}",
                learner_id="LRN-001",
                assessment_id="ASM-001",
                attempt_no=1,
                submitted_at=submitted_at,
                status="SUBMITTED",
                content_reference=f"ref-{i}",
                content_hash=f"hash-{i:064x}",
            )
        )

    # ── Similarity Reports ───────────────────────────────────────────────
    generated_at = datetime(2026, 2, 16, 8, 0, 0)

    # SUB-1: flagged, with rule
    session.add(
        SimilarityReport(
            report_id="SIM-SUB-2026-000001-01",
            submission_id="SUB-2026-000001",
            rule_id="RULE-001",
            report_no=1,
            similarity_score=85.50,
            matched_source_count=5,
            review_required=True,
            report_status="REVIEW_REQUIRED",
            generated_at=generated_at,
        )
    )

    # SUB-2: flagged, with rule
    session.add(
        SimilarityReport(
            report_id="SIM-SUB-2026-000002-01",
            submission_id="SUB-2026-000002",
            rule_id="RULE-001",
            report_no=1,
            similarity_score=92.00,
            matched_source_count=8,
            review_required=True,
            report_status="REVIEW_REQUIRED",
            generated_at=generated_at,
        )
    )

    # SUB-3: not flagged, with rule
    session.add(
        SimilarityReport(
            report_id="SIM-SUB-2026-000003-01",
            submission_id="SUB-2026-000003",
            rule_id="RULE-001",
            report_no=1,
            similarity_score=45.00,
            matched_source_count=2,
            review_required=False,
            report_status="MONITOR",
            generated_at=generated_at,
        )
    )

    # SUB-5: not flagged, NO rule (rule_id=None)
    session.add(
        SimilarityReport(
            report_id="SIM-SUB-2026-000005-01",
            submission_id="SUB-2026-000005",
            rule_id=None,
            report_no=1,
            similarity_score=30.00,
            matched_source_count=1,
            review_required=False,
            report_status="NO_REVIEW",
            generated_at=generated_at,
        )
    )

    # SUB-4: no report

    session.commit()

    yield session

    session.close()
    engine.dispose()


# ── get_submissions tests ────────────────────────────────────────────────────


class TestGetSubmissions:
    """Tests for get_submissions() — Requirements 7.1, 7.3, 7.4."""

    def test_returns_all_submissions_by_default(self, db_session: Session):
        """Without the flagged filter, all 5 submissions are returned."""
        result = get_submissions(db_session)
        assert isinstance(result, PaginatedSubmissions)
        assert result.total_count == 5
        assert len(result.items) == 5
        assert result.page == 1
        assert result.page_size == 20

    def test_flagged_filter_returns_only_flagged(self, db_session: Session):
        """flagged=True returns only submissions whose report has review_required=True."""
        result = get_submissions(db_session, flagged=True)
        assert result.total_count == 2
        assert len(result.items) == 2
        for item in result.items:
            assert item.review_required is True
            assert item.similarity_score is not None

    def test_flagged_filter_correct_ids(self, db_session: Session):
        """The two flagged submissions are SUB-2026-000001 and SUB-2026-000002."""
        result = get_submissions(db_session, flagged=True)
        ids = {item.submission_id for item in result.items}
        assert ids == {"SUB-2026-000001", "SUB-2026-000002"}

    def test_pagination_first_page(self, db_session: Session):
        """Page 1 with page_size=2 returns 2 items."""
        result = get_submissions(db_session, page=1, page_size=2)
        assert result.total_count == 5
        assert len(result.items) == 2
        assert result.page == 1
        assert result.page_size == 2

    def test_pagination_second_page(self, db_session: Session):
        """Page 2 with page_size=2 returns 2 items."""
        result = get_submissions(db_session, page=2, page_size=2)
        assert result.total_count == 5
        assert len(result.items) == 2
        assert result.page == 2

    def test_pagination_last_partial_page(self, db_session: Session):
        """Page 3 with page_size=2 returns the remaining 1 item."""
        result = get_submissions(db_session, page=3, page_size=2)
        assert result.total_count == 5
        assert len(result.items) == 1

    def test_pagination_empty_page_beyond_data(self, db_session: Session):
        """A page beyond the data range returns an empty items list."""
        result = get_submissions(db_session, page=10, page_size=2)
        assert result.total_count == 5
        assert len(result.items) == 0

    def test_flagged_pagination_respects_total(self, db_session: Session):
        """Flagged filter with pagination still reports total_count=2."""
        result = get_submissions(db_session, flagged=True, page=1, page_size=1)
        assert result.total_count == 2
        assert len(result.items) == 1

    def test_submission_without_report_has_null_fields(self, db_session: Session):
        """Submissions without a report have None for similarity_score and review_required."""
        result = get_submissions(db_session)
        no_report = [
            item for item in result.items if item.submission_id == "SUB-2026-000004"
        ]
        assert len(no_report) == 1
        assert no_report[0].similarity_score is None
        assert no_report[0].review_required is None

    def test_submission_with_report_populates_fields(self, db_session: Session):
        """Submissions with a report have populated similarity_score and review_required."""
        result = get_submissions(db_session)
        with_report = [
            item for item in result.items if item.submission_id == "SUB-2026-000003"
        ]
        assert len(with_report) == 1
        assert with_report[0].similarity_score == 45.00
        assert with_report[0].review_required is False


# ── get_submission_detail tests ──────────────────────────────────────────────


class TestGetSubmissionDetail:
    """Tests for get_submission_detail() — Requirements 7.2, 7.5."""

    def test_returns_submission_with_report(self, db_session: Session):
        """Detail includes the linked SimilarityReport summary."""
        result = get_submission_detail(db_session, "SUB-2026-000001")
        assert isinstance(result, SubmissionDetail)
        assert result.submission_id == "SUB-2026-000001"
        assert result.learner_id == "LRN-001"
        assert result.assessment_id == "ASM-001"
        assert result.content_reference == "ref-1"
        assert result.report is not None
        assert result.report.report_id == "SIM-SUB-2026-000001-01"
        assert result.report.similarity_score == 85.50
        assert result.report.review_required is True
        assert result.report.report_status == "REVIEW_REQUIRED"

    def test_returns_submission_without_report(self, db_session: Session):
        """Detail for a submission without a report has report=None."""
        result = get_submission_detail(db_session, "SUB-2026-000004")
        assert result.submission_id == "SUB-2026-000004"
        assert result.report is None
        assert result.similarity_score is None
        assert result.review_required is None
        assert result.content_reference == "ref-4"

    def test_404_for_unknown_submission(self, db_session: Session):
        """Unknown submission_id raises HTTP 404 with correct detail message."""
        with pytest.raises(HTTPException) as exc_info:
            get_submission_detail(db_session, "NON-EXISTENT")
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Submission not found"


# ── get_similarity_report tests ──────────────────────────────────────────────


class TestGetSimilarityReport:
    """Tests for get_similarity_report() — Requirement 7.6."""

    def test_returns_report_with_rule(self, db_session: Session):
        """Report detail includes the linked IntegrityRule summary."""
        result = get_similarity_report(db_session, "SIM-SUB-2026-000001-01")
        assert isinstance(result, SimilarityReportDetail)
        assert result.report_id == "SIM-SUB-2026-000001-01"
        assert result.submission_id == "SUB-2026-000001"
        assert result.similarity_score == 85.50
        assert result.review_required is True
        assert result.report_status == "REVIEW_REQUIRED"
        assert result.report_no == 1
        assert result.matched_source_count == 5
        assert result.rule_id == "RULE-001"
        assert result.rule is not None
        assert result.rule.rule_id == "RULE-001"
        assert result.rule.rule_name == "Review Threshold"
        assert result.rule.action_type == "REVIEW"

    def test_returns_report_without_rule(self, db_session: Session):
        """Report with no linked IntegrityRule has rule=None and rule_id=None."""
        result = get_similarity_report(db_session, "SIM-SUB-2026-000005-01")
        assert result.report_id == "SIM-SUB-2026-000005-01"
        assert result.rule_id is None
        assert result.rule is None
        assert result.review_required is False
        assert result.similarity_score == 30.00

    def test_404_for_unknown_report(self, db_session: Session):
        """Unknown report_id raises HTTP 404 with correct detail message."""
        with pytest.raises(HTTPException) as exc_info:
            get_similarity_report(db_session, "NON-EXISTENT")
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Similarity report not found"
