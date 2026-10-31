"""
tests/services/test_case_service.py

Verification tests for the case management functions in
backend/services/case_service.py:
    get_cases, get_case_detail, update_case_status

Uses an in-memory SQLite database so no MySQL instance is needed.

Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7
"""

import os

# Point the app's DATABASE_URL at a throwaway SQLite file BEFORE importing any
# backend module. The engine created in backend.database is lazy and never
# connects, so the import succeeds without the mysql-connector dependency.
os.environ.setdefault("DATABASE_URL", "sqlite:///./_case_test_unused.db")

from datetime import date, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

# Render BigInteger as INTEGER for SQLite so PK autoincrement works.
@compiles(BigInteger, "sqlite")
def _big_int_as_integer_sqlite(element, compiler, **kw):  # noqa: ARG001
    return "INTEGER"


from backend.database import Base
from backend.models.assessment import Assessment
from backend.models.audit_log import AuditLog
from backend.models.case_event import CaseEvent
from backend.models.case_reviewer import CaseReviewer
from backend.models.decision import Decision
from backend.models.integrity_case import IntegrityCase
from backend.models.integrity_rule import IntegrityRule
from backend.models.learner import Learner
from backend.models.reviewer import Reviewer
from backend.models.similarity_report import SimilarityReport
from backend.models.submission import Submission
from backend.schemas.cases import (
    CaseDetail,
    CaseStatus,
    CaseStatusUpdate,
    PaginatedCases,
    Priority,
)
from backend.services.case_service import (
    get_cases,
    get_case_detail,
    update_case_status,
)


# ── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def db_session():
    """
    Module-scoped in-memory SQLite session with test data pre-loaded.

    Data set:
      * 1 Learner, 1 Assessment, 1 IntegrityRule, 2 Reviewers
      * 1 Submission, 1 SimilarityReport (flagged)
      * 3 IntegrityCases:
          INT-001: OPEN,   HIGH,   no conflict
          INT-002: UNDER_REVIEW, MEDIUM, has a reviewer with CONFLICT
          INT-003: DECIDED, LOW,   has a final Decision
      * CaseReviewers, Decision, CaseEvent rows as needed
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
            Reviewer.__table__,
            IntegrityCase.__table__,
            CaseReviewer.__table__,
            Decision.__table__,
            CaseEvent.__table__,
            AuditLog.__table__,
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

    # ── Reviewers ────────────────────────────────────────────────────────
    for i, (rid, role) in enumerate(
        [("REV-001", "INSTRUCTOR"), ("REV-002", "ACADEMIC_ADMIN")], start=1
    ):
        session.add(
            Reviewer(
                reviewer_id=rid,
                full_name=f"Reviewer {i}",
                email=f"reviewer{i}@test.edu",
                reviewer_role=role,
                status="ACTIVE",
                created_at=datetime(2026, 1, 1),
            )
        )

    # ── Submissions + Reports (one per case — report_id is unique) ───────
    for i in range(1, 6):
        session.add(
            Submission(
                submission_id=f"SUB-2026-{i:06d}",
                learner_id="LRN-001",
                assessment_id="ASM-001",
                attempt_no=1,
                submitted_at=datetime(2026, 2, 15, 10, 0, 0),
                status="SUBMITTED",
                content_reference=f"ref-{i}",
                content_hash=f"hash-{i:064x}",
            )
        )
        session.add(
            SimilarityReport(
                report_id=f"SIM-SUB-2026-{i:06d}-01",
                submission_id=f"SUB-2026-{i:06d}",
                rule_id="RULE-001",
                report_no=1,
                similarity_score=85.50,
                matched_source_count=5,
                review_required=True,
                report_status="REVIEW_REQUIRED",
                generated_at=datetime(2026, 2, 16, 8, 0, 0),
            )
        )

    # ── Integrity Cases ──────────────────────────────────────────────────
    cases_data = [
        ("INT-2026-000001", "SIM-SUB-2026-000001-01", "OPEN", "HIGH",
         datetime(2026, 2, 17), None),
        ("INT-2026-000002", "SIM-SUB-2026-000002-01", "UNDER_REVIEW", "MEDIUM",
         datetime(2026, 2, 17, 1), None),
        ("INT-2026-000003", "SIM-SUB-2026-000003-01", "DECIDED", "LOW",
         datetime(2026, 2, 17, 2), None),
    ]
    for case_id, report_id, status, priority, opened_at, closed_at in cases_data:
        session.add(
            IntegrityCase(
                case_id=case_id,
                report_id=report_id,
                case_status=status,
                priority=priority,
                opened_at=opened_at,
                closed_at=closed_at,
            )
        )

    # ── Case Reviewers ───────────────────────────────────────────────────
    # INT-001: PRIMARY reviewer, no conflict
    session.add(
        CaseReviewer(
            assignment_id=1,
            case_id="INT-2026-000001",
            reviewer_id="REV-001",
            assignment_role="PRIMARY",
            assigned_at=datetime(2026, 2, 17, 3),
            conflict_status="PENDING",
        )
    )
    # INT-002: PRIMARY reviewer + SECONDARY reviewer with CONFLICT
    session.add(
        CaseReviewer(
            assignment_id=2,
            case_id="INT-2026-000002",
            reviewer_id="REV-001",
            assignment_role="PRIMARY",
            assigned_at=datetime(2026, 2, 17, 4),
            conflict_status="PENDING",
        )
    )
    session.add(
        CaseReviewer(
            assignment_id=3,
            case_id="INT-2026-000002",
            reviewer_id="REV-002",
            assignment_role="SECONDARY",
            assigned_at=datetime(2026, 2, 17, 5),
            unassigned_at=datetime(2026, 2, 18),
            conflict_status="CONFLICT",
            conflict_reason="Personal relationship with learner",
        )
    )
    # INT-003: PRIMARY reviewer (REV-002)
    session.add(
        CaseReviewer(
            assignment_id=4,
            case_id="INT-2026-000003",
            reviewer_id="REV-002",
            assignment_role="PRIMARY",
            assigned_at=datetime(2026, 2, 17, 6),
            conflict_status="PENDING",
        )
    )

    # ── Decision for INT-003 ─────────────────────────────────────────────
    session.add(
        Decision(
            decision_id=1,
            case_id="INT-2026-000003",
            reviewer_id="REV-002",
            decision_outcome="VIOLATION",
            rationale="Plagiarism confirmed via similarity report",
            decided_at=datetime(2026, 2, 20),
            is_final=True,
        )
    )

    # ── Case Events ──────────────────────────────────────────────────────
    for case_id, etype, occurred_at in [
        ("INT-2026-000001", "CASE_CREATED", datetime(2026, 2, 17, 0)),
        ("INT-2026-000001", "REVIEWER_ASSIGNED", datetime(2026, 2, 17, 3)),
        ("INT-2026-000002", "CASE_CREATED", datetime(2026, 2, 17, 1)),
        ("INT-2026-000003", "CASE_CREATED", datetime(2026, 2, 17, 2)),
        ("INT-2026-000003", "DECISION_RECORDED", datetime(2026, 2, 20)),
    ]:
        session.add(
            CaseEvent(
                case_id=case_id,
                event_type=etype,
                actor_role="SYSTEM",
                occurred_at=occurred_at,
            )
        )

    session.commit()

    yield session

    session.close()
    engine.dispose()


# ── get_cases tests ──────────────────────────────────────────────────────────


class TestGetCases:
    """Tests for get_cases() — Requirements 8.1, 8.7."""

    def test_returns_all_cases_by_default(self, db_session: Session):
        """Without filters, all 3 cases are returned."""
        result = get_cases(db_session)
        assert isinstance(result, PaginatedCases)
        assert result.total_count == 3
        assert len(result.items) == 3
        assert result.page == 1
        assert result.page_size == 20

    def test_filter_by_status(self, db_session: Session):
        """Filtering by status=OPEN returns only OPEN cases."""
        result = get_cases(db_session, status=CaseStatus.OPEN)
        assert result.total_count == 1
        assert len(result.items) == 1
        assert result.items[0].case_id == "INT-2026-000001"
        assert result.items[0].case_status == CaseStatus.OPEN

    def test_filter_by_priority(self, db_session: Session):
        """Filtering by priority=HIGH returns only HIGH priority cases."""
        result = get_cases(db_session, priority=Priority.HIGH)
        assert result.total_count == 1
        assert result.items[0].case_id == "INT-2026-000001"
        assert result.items[0].priority == "HIGH"

    def test_filter_by_assigned_reviewer_id(self, db_session: Session):
        """Filtering by assigned_reviewer_id=REV-002 returns cases with that reviewer."""
        result = get_cases(db_session, assigned_reviewer_id="REV-002")
        assert result.total_count == 2
        ids = {item.case_id for item in result.items}
        assert ids == {"INT-2026-000002", "INT-2026-000003"}

    def test_filter_by_assigned_reviewer_no_match(self, db_session: Session):
        """Filtering by a non-existent reviewer returns 0 cases."""
        result = get_cases(db_session, assigned_reviewer_id="REV-999")
        assert result.total_count == 0
        assert len(result.items) == 0

    def test_combined_filter_status_and_priority(self, db_session: Session):
        """Combining status and priority filters."""
        result = get_cases(
            db_session, status=CaseStatus.UNDER_REVIEW, priority=Priority.MEDIUM
        )
        assert result.total_count == 1
        assert result.items[0].case_id == "INT-2026-000002"

    def test_has_conflict_true(self, db_session: Session):
        """INT-2026-000002 has a reviewer with CONFLICT → has_conflict=True."""
        result = get_cases(db_session, status=CaseStatus.UNDER_REVIEW)
        assert result.items[0].has_conflict is True

    def test_has_conflict_false(self, db_session: Session):
        """INT-2026-000001 has no CONFLICT reviewers → has_conflict=False."""
        result = get_cases(db_session, status=CaseStatus.OPEN)
        assert result.items[0].has_conflict is False

    def test_pagination_first_page(self, db_session: Session):
        """Page 1 with page_size=2 returns 2 items."""
        result = get_cases(db_session, page=1, page_size=2)
        assert result.total_count == 3
        assert len(result.items) == 2
        assert result.page == 1
        assert result.page_size == 2

    def test_pagination_second_page(self, db_session: Session):
        """Page 2 with page_size=2 returns the remaining 1 item."""
        result = get_cases(db_session, page=2, page_size=2)
        assert result.total_count == 3
        assert len(result.items) == 1
        assert result.page == 2

    def test_pagination_empty_page_beyond_data(self, db_session: Session):
        """A page beyond the data range returns an empty items list."""
        result = get_cases(db_session, page=10, page_size=2)
        assert result.total_count == 3
        assert len(result.items) == 0


# ── get_case_detail tests ────────────────────────────────────────────────────


class TestGetCaseDetail:
    """Tests for get_case_detail() — Requirements 8.2, 8.5."""

    def test_returns_case_with_report(self, db_session: Session):
        """Detail includes the linked SimilarityReport summary."""
        result = get_case_detail(db_session, "INT-2026-000001")
        assert isinstance(result, CaseDetail)
        assert result.case_id == "INT-2026-000001"
        assert result.report_summary is not None
        assert result.report_summary.report_id == "SIM-SUB-2026-000001-01"
        assert result.report_summary.similarity_score == 85.50
        assert result.report_summary.review_required is True

    def test_returns_case_with_reviewers(self, db_session: Session):
        """Detail includes the list of assigned reviewers."""
        result = get_case_detail(db_session, "INT-2026-000002")
        assert len(result.reviewers) == 2
        reviewer_ids = {r.reviewer_id for r in result.reviewers}
        assert reviewer_ids == {"REV-001", "REV-002"}

    def test_returns_case_with_decision_summary(self, db_session: Session):
        """Detail includes the final decision summary when present."""
        result = get_case_detail(db_session, "INT-2026-000003")
        assert result.decision_summary is not None
        assert result.decision_summary.decision_outcome == "VIOLATION"
        assert result.decision_summary.is_final is True

    def test_returns_case_without_decision(self, db_session: Session):
        """Detail has decision_summary=None when no decision exists."""
        result = get_case_detail(db_session, "INT-2026-000001")
        assert result.decision_summary is None

    def test_returns_case_with_events(self, db_session: Session):
        """Detail includes the case event timeline."""
        result = get_case_detail(db_session, "INT-2026-000003")
        assert len(result.events) >= 2
        event_types = {e.event_type for e in result.events}
        assert "CASE_CREATED" in event_types
        assert "DECISION_RECORDED" in event_types

    def test_has_conflict_in_detail(self, db_session: Session):
        """Detail has has_conflict=True when a reviewer has CONFLICT."""
        result = get_case_detail(db_session, "INT-2026-000002")
        assert result.has_conflict is True

    def test_has_no_conflict_in_detail(self, db_session: Session):
        """Detail has has_conflict=False when no reviewer has CONFLICT."""
        result = get_case_detail(db_session, "INT-2026-000001")
        assert result.has_conflict is False

    def test_404_for_unknown_case(self, db_session: Session):
        """Unknown case_id raises HTTP 404."""
        with pytest.raises(HTTPException) as exc_info:
            get_case_detail(db_session, "INT-2026-999999")
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    def test_case_status_enum_in_detail(self, db_session: Session):
        """case_status is returned as a CaseStatus enum."""
        result = get_case_detail(db_session, "INT-2026-000001")
        assert result.case_status == CaseStatus.OPEN


# ── update_case_status tests ────────────────────────────────────────────────


class TestUpdateCaseStatus:
    """Tests for update_case_status() — Requirements 8.3, 8.4, 8.5, 8.6."""

    def test_valid_transition_updates_status(self, db_session: Session):
        """OPEN → UNDER_REVIEW is a valid transition and updates the status."""
        payload = CaseStatusUpdate(
            case_status=CaseStatus.UNDER_REVIEW,
            actor_role="REVIEWER",
            actor_ref="REV-001",
        )
        result = update_case_status(db_session, "INT-2026-000001", payload)
        assert isinstance(result, CaseDetail)
        assert result.case_status == CaseStatus.UNDER_REVIEW
        db_session.commit()

    def test_invalid_transition_raises_422(self, db_session: Session):
        """CLOSED → OPEN is an invalid transition → HTTP 422."""
        # First close the case via valid path: OPEN is already closed above,
        # so use a fresh case. Let's close INT-003 (DECIDED → CLOSED is valid).
        payload = CaseStatusUpdate(
            case_status=CaseStatus.CLOSED, actor_role="ACADEMIC_ADMIN"
        )
        update_case_status(db_session, "INT-2026-000003", payload)
        db_session.commit()

        # Now try CLOSED → OPEN (invalid)
        bad_payload = CaseStatusUpdate(
            case_status=CaseStatus.OPEN, actor_role="ACADEMIC_ADMIN"
        )
        with pytest.raises(HTTPException) as exc_info:
            update_case_status(db_session, "INT-2026-000003", bad_payload)
        assert exc_info.value.status_code == 422
        assert "Invalid status transition" in exc_info.value.detail

    def test_closed_is_terminal(self, db_session: Session):
        """No transitions out of CLOSED are valid."""
        # INT-2026-000003 is now CLOSED from the previous test
        for target in [CaseStatus.OPEN, CaseStatus.UNDER_REVIEW,
                        CaseStatus.AWAITING_INFORMATION, CaseStatus.DECIDED,
                        CaseStatus.APPEAL_PENDING]:
            payload = CaseStatusUpdate(case_status=target, actor_role="SYSTEM")
            with pytest.raises(HTTPException) as exc_info:
                update_case_status(db_session, "INT-2026-000003", payload)
            assert exc_info.value.status_code == 422

    def test_404_for_unknown_case(self, db_session: Session):
        """Unknown case_id raises HTTP 404."""
        payload = CaseStatusUpdate(
            case_status=CaseStatus.UNDER_REVIEW, actor_role="SYSTEM"
        )
        with pytest.raises(HTTPException) as exc_info:
            update_case_status(db_session, "INT-2026-999999", payload)
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    def test_inserts_status_changed_case_event(self, db_session: Session):
        """A successful status update inserts a STATUS_CHANGED CaseEvent
        (Requirement 8.4)."""
        # INT-002 is UNDER_REVIEW → can go to AWAITING_INFORMATION
        before = (
            db_session.query(CaseEvent)
            .filter(
                CaseEvent.case_id == "INT-2026-000002",
                CaseEvent.event_type == "STATUS_CHANGED",
            )
            .count()
        )
        assert before == 0

        payload = CaseStatusUpdate(
            case_status=CaseStatus.AWAITING_INFORMATION, actor_role="REVIEWER"
        )
        update_case_status(db_session, "INT-2026-000002", payload)
        db_session.commit()

        after = (
            db_session.query(CaseEvent)
            .filter(
                CaseEvent.case_id == "INT-2026-000002",
                CaseEvent.event_type == "STATUS_CHANGED",
            )
            .count()
        )
        assert after == 1

        event = (
            db_session.query(CaseEvent)
            .filter(
                CaseEvent.case_id == "INT-2026-000002",
                CaseEvent.event_type == "STATUS_CHANGED",
            )
            .one()
        )
        assert event.previous_status == "UNDER_REVIEW"
        assert event.new_status == "AWAITING_INFORMATION"
        assert event.actor_role == "REVIEWER"

    def test_writes_audit_log(self, db_session: Session):
        """A successful status update writes an AuditLog for IntegrityCase UPDATE."""
        before = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "IntegrityCase",
                AuditLog.entity_id == "INT-2026-000002",
                AuditLog.action == "UPDATE",
            )
            .count()
        )
        # INT-002 is now AWAITING_INFORMATION → can go to UNDER_REVIEW
        payload = CaseStatusUpdate(
            case_status=CaseStatus.UNDER_REVIEW,
            actor_role="ACADEMIC_ADMIN",
            actor_ref="REV-002",
        )
        update_case_status(db_session, "INT-2026-000002", payload)
        db_session.commit()

        after = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "IntegrityCase",
                AuditLog.entity_id == "INT-2026-000002",
                AuditLog.action == "UPDATE",
            )
            .count()
        )
        assert after == before + 1

        log = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "IntegrityCase",
                AuditLog.entity_id == "INT-2026-000002",
            )
            .order_by(AuditLog.created_at.desc())
            .first()
        )
        assert log.old_values is not None
        assert log.old_values["case_status"] == "AWAITING_INFORMATION"
        assert log.new_values["case_status"] == "UNDER_REVIEW"
        assert log.actor_role == "ACADEMIC_ADMIN"
        assert log.actor_ref == "REV-002"

    def test_sets_closed_at_on_close(self, db_session: Session):
        """Transitioning to CLOSED sets closed_at if it was null."""
        # INT-002 is now UNDER_REVIEW → can go to CLOSED
        payload = CaseStatusUpdate(
            case_status=CaseStatus.CLOSED, actor_role="SYSTEM"
        )
        result = update_case_status(db_session, "INT-2026-000002", payload)
        assert result.closed_at is not None
        db_session.commit()

    def test_does_not_commit_on_rollback(self, db_session: Session):
        """update_case_status must not commit; rollback discards changes."""
        session = db_session
        session.add(
            IntegrityCase(
                case_id="INT-2026-ROLLBACK",
                report_id="SIM-SUB-2026-000004-01",
                case_status="OPEN",
                priority="LOW",
                opened_at=datetime(2026, 3, 1),
                closed_at=None,
            )
        )
        session.commit()

        payload = CaseStatusUpdate(
            case_status=CaseStatus.UNDER_REVIEW, actor_role="SYSTEM"
        )
        update_case_status(session, "INT-2026-ROLLBACK", payload)

        # Roll back without committing
        session.rollback()

        # Verify the case is still OPEN (rollback discarded the update)
        case = session.get(IntegrityCase, "INT-2026-ROLLBACK")
        assert case.case_status == "OPEN"

    def test_open_to_closed_valid(self, db_session: Session):
        """OPEN → CLOSED is a valid direct transition."""
        session = db_session
        session.add(
            IntegrityCase(
                case_id="INT-2026-DIRECT",
                report_id="SIM-SUB-2026-000005-01",
                case_status="OPEN",
                priority="LOW",
                opened_at=datetime(2026, 3, 1),
                closed_at=None,
            )
        )
        session.commit()

        payload = CaseStatusUpdate(
            case_status=CaseStatus.CLOSED, actor_role="SYSTEM"
        )
        result = update_case_status(session, "INT-2026-DIRECT", payload)
        assert result.case_status == CaseStatus.CLOSED
        assert result.closed_at is not None
        session.commit()
