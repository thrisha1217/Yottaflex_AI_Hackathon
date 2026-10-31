"""
tests/services/test_reviewer_service.py

Service-level tests for the reviewer assignment and conflict operations in
backend/services/case_service.py:
    assign_reviewer, update_conflict, get_reviewers

Uses an in-memory SQLite database so no MySQL instance is needed.

Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 21.3, 21.4
"""

import os

# Point the app's DATABASE_URL at a throwaway SQLite file BEFORE importing any
# backend module. The engine created in backend.database is lazy and never
# connects, so the import succeeds without the mysql-connector dependency.
os.environ.setdefault("DATABASE_URL", "sqlite:///./_reviewer_test_unused.db")

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
from backend.models.integrity_case import IntegrityCase
from backend.models.integrity_rule import IntegrityRule
from backend.models.learner import Learner
from backend.models.reviewer import Reviewer
from backend.models.similarity_report import SimilarityReport
from backend.models.submission import Submission
from backend.schemas.reviewers import (
    CaseReviewerCreate,
    CaseReviewerOut,
    ConflictUpdate,
    PaginatedReviewers,
    ReviewerOut,
)
from backend.services.case_service import (
    assign_reviewer,
    get_reviewers,
    update_conflict,
)


# ── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def db_session():
    """
    Module-scoped in-memory SQLite session with test data pre-loaded.

    Data set:
      * 1 Learner, 1 Assessment, 1 IntegrityRule
      * 3 Reviewers: REV-001 (ACTIVE), REV-002 (ACTIVE), REV-003 (INACTIVE)
      * 4 Submissions + SimilarityReports
      * 3 IntegrityCases:
          INT-001: OPEN, no reviewer conflict
          INT-002: UNDER_REVIEW, has reviewer with CONFLICT
          INT-003: CLOSED, has a final Decision
      * CaseReviewers, CaseEvents as needed
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
            AuditLog.__table__,
            CaseEvent.__table__,
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
    # REV-001: ACTIVE INSTRUCTOR
    # REV-002: ACTIVE ACADEMIC_ADMIN
    # REV-003: INACTIVE REVIEWER
    for rid, role, status in [
        ("REV-001", "INSTRUCTOR", "ACTIVE"),
        ("REV-002", "ACADEMIC_ADMIN", "ACTIVE"),
        ("REV-003", "REVIEWER", "INACTIVE"),
    ]:
        session.add(
            Reviewer(
                reviewer_id=rid,
                full_name=f"Reviewer {rid[-3:]}",
                email=f"{rid.lower()}@test.edu",
                reviewer_role=role,
                status=status,
                created_at=datetime(2026, 1, 1),
            )
        )

    # ── Submissions + Reports (one per case + extras) ─────────────────────
    for i in range(1, 7):
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
        ("INT-2026-000003", "SIM-SUB-2026-000003-01", "CLOSED", "LOW",
         datetime(2026, 2, 17, 2), datetime(2026, 2, 25)),
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
    # INT-001: PRIMARY reviewer (REV-001), no conflict
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
    # INT-002: PRIMARY reviewer (REV-001), SECONDARY reviewer (REV-002) with CONFLICT
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
    # INT-003: CLOSED case with a reviewer
    session.add(
        CaseReviewer(
            assignment_id=4,
            case_id="INT-2026-000003",
            reviewer_id="REV-001",
            assignment_role="PRIMARY",
            assigned_at=datetime(2026, 2, 17, 6),
            conflict_status="PENDING",
        )
    )

    # ── Case Events ──────────────────────────────────────────────────────
    for case_id, etype, occurred_at in [
        ("INT-2026-000001", "CASE_CREATED", datetime(2026, 2, 17, 0)),
        ("INT-2026-000001", "REVIEWER_ASSIGNED", datetime(2026, 2, 17, 3)),
        ("INT-2026-000002", "CASE_CREATED", datetime(2026, 2, 17, 1)),
        ("INT-2026-000003", "CASE_CREATED", datetime(2026, 2, 17, 2)),
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


# ── assign_reviewer tests ────────────────────────────────────────────────────


class TestAssignReviewer:
    """Tests for assign_reviewer() — Requirements 9.1, 9.5, 21.3."""

    def test_assigns_active_reviewer(self, db_session: Session):
        """Assigning an ACTIVE reviewer to an OPEN case succeeds
        (Requirement 9.1)."""
        payload = CaseReviewerCreate(
            reviewer_id="REV-002",
            assignment_role="SECONDARY",
            actor_role="ACADEMIC_ADMIN",
        )
        result = assign_reviewer(db_session, "INT-2026-000001", payload)
        assert isinstance(result, CaseReviewerOut)
        assert result.case_id == "INT-2026-000001"
        assert result.reviewer_id == "REV-002"
        assert result.assignment_role == "SECONDARY"
        assert result.conflict_status == "PENDING"
        assert result.unassigned_at is None
        db_session.commit()

    def test_404_for_unknown_case(self, db_session: Session):
        """Unknown case_id raises HTTP 404."""
        payload = CaseReviewerCreate(
            reviewer_id="REV-001",
            assignment_role="PRIMARY",
            actor_role="SYSTEM",
        )
        with pytest.raises(HTTPException) as exc_info:
            assign_reviewer(db_session, "INT-2026-999999", payload)
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    def test_404_for_unknown_reviewer(self, db_session: Session):
        """Unknown reviewer_id raises HTTP 404."""
        payload = CaseReviewerCreate(
            reviewer_id="REV-999",
            assignment_role="PRIMARY",
            actor_role="SYSTEM",
        )
        with pytest.raises(HTTPException) as exc_info:
            assign_reviewer(db_session, "INT-2026-000001", payload)
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    def test_422_for_inactive_reviewer(self, db_session: Session):
        """Assigning an INACTIVE reviewer raises HTTP 422 (Requirement 21.3)."""
        payload = CaseReviewerCreate(
            reviewer_id="REV-003",  # INACTIVE
            assignment_role="PRIMARY",
            actor_role="SYSTEM",
        )
        with pytest.raises(HTTPException) as exc_info:
            assign_reviewer(db_session, "INT-2026-000001", payload)
        assert exc_info.value.status_code == 422
        assert "not active" in exc_info.value.detail

    def test_409_for_active_conflict(self, db_session: Session):
        """Assigning a reviewer who already has a CONFLICT on the same case
        raises HTTP 409 (Requirement 9.5).

        REV-002 already has a CONFLICT assignment on INT-2026-000002.
        """
        payload = CaseReviewerCreate(
            reviewer_id="REV-002",
            assignment_role="PRIMARY",
            actor_role="ACADEMIC_ADMIN",
        )
        with pytest.raises(HTTPException) as exc_info:
            assign_reviewer(db_session, "INT-2026-000002", payload)
        assert exc_info.value.status_code == 409
        assert "conflict" in exc_info.value.detail.lower()

    def test_inserts_reviewer_assigned_case_event(self, db_session: Session):
        """assign_reviewer inserts a REVIEWER_ASSIGNED CaseEvent
        (Requirement 9.1 side-effect)."""
        before = (
            db_session.query(CaseEvent)
            .filter(
                CaseEvent.case_id == "INT-2026-000003",
                CaseEvent.event_type == "REVIEWER_ASSIGNED",
            )
            .count()
        )
        assert before == 0

        payload = CaseReviewerCreate(
            reviewer_id="REV-002",
            assignment_role="SECONDARY",
            actor_role="ACADEMIC_ADMIN",
        )
        assign_reviewer(db_session, "INT-2026-000003", payload)
        db_session.commit()

        after = (
            db_session.query(CaseEvent)
            .filter(
                CaseEvent.case_id == "INT-2026-000003",
                CaseEvent.event_type == "REVIEWER_ASSIGNED",
            )
            .count()
        )
        assert after == 1

    def test_writes_audit_log_for_insert(self, db_session: Session):
        """assign_reviewer writes an AuditLog for the CaseReviewer INSERT
        (Requirement 13.4)."""
        before = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "CaseReviewer",
                AuditLog.action == "INSERT",
            )
            .count()
        )

        payload = CaseReviewerCreate(
            reviewer_id="REV-002",
            assignment_role="PRIMARY",
            actor_role="REVIEWER",
        )
        assign_reviewer(db_session, "INT-2026-000003", payload)
        db_session.commit()

        after = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "CaseReviewer",
                AuditLog.action == "INSERT",
            )
            .count()
        )
        assert after == before + 1

        log = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "CaseReviewer",
                AuditLog.action == "INSERT",
            )
            .order_by(AuditLog.created_at.desc())
            .first()
        )
        assert log.old_values is None  # INSERT has no old values
        assert log.new_values is not None
        assert log.new_values["case_id"] == "INT-2026-000003"
        assert log.new_values["reviewer_id"] == "REV-002"
        assert log.actor_role == "REVIEWER"

    def test_does_not_commit(self, db_session: Session):
        """assign_reviewer does not commit; rollback discards the new record."""
        session = db_session
        session.add(
            IntegrityCase(
                case_id="INT-2026-ASSIGNROLLBACK",
                report_id="SIM-SUB-2026-000004-01",
                case_status="OPEN",
                priority="LOW",
                opened_at=datetime(2026, 3, 1),
                closed_at=None,
            )
        )
        session.commit()

        payload = CaseReviewerCreate(
            reviewer_id="REV-001",
            assignment_role="SECONDARY",
            actor_role="SYSTEM",
        )
        assign_reviewer(session, "INT-2026-ASSIGNROLLBACK", payload)
        session.rollback()

        # The assignment should not exist after rollback
        count = (
            session.query(CaseReviewer)
            .filter(
                CaseReviewer.case_id == "INT-2026-ASSIGNROLLBACK",
                CaseReviewer.reviewer_id == "REV-001",
            )
            .count()
        )
        assert count == 0


# ── update_conflict tests ────────────────────────────────────────────────────


class TestUpdateConflict:
    """Tests for update_conflict() — Requirements 9.2, 9.3, 9.4, 21.4."""

    def test_sets_conflict_status_and_unassigned_at(self, db_session: Session):
        """update_conflict sets conflict_status=CONFLICT and unassigned_at
        (Requirements 9.2, 9.3)."""
        # Assignment 1 (INT-001, REV-001, PRIMARY, PENDING)
        payload = ConflictUpdate(
            conflict_status="CONFLICT",
            conflict_reason="New conflict discovered",
            actor_role="ACADEMIC_ADMIN",
            actor_ref="REV-002",
        )
        result = update_conflict(db_session, "INT-2026-000001", 1, payload)
        assert isinstance(result, CaseReviewerOut)
        assert result.conflict_status == "CONFLICT"
        assert result.unassigned_at is not None
        assert result.conflict_reason == "New conflict discovered"
        db_session.commit()

    def test_inserts_reviewer_conflict_declared_case_event(
        self, db_session: Session
    ):
        """update_conflict inserts a REVIEWER_CONFLICT_DECLARED CaseEvent
        (Requirement 9.4)."""
        # Assignment 2 (INT-002, REV-001, PRIMARY, PENDING)
        before = (
            db_session.query(CaseEvent)
            .filter(
                CaseEvent.case_id == "INT-2026-000002",
                CaseEvent.event_type == "REVIEWER_CONFLICT_DECLARED",
            )
            .count()
        )
        assert before == 0

        payload = ConflictUpdate(
            conflict_status="CONFLICT",
            actor_role="ACADEMIC_ADMIN",
        )
        update_conflict(db_session, "INT-2026-000002", 2, payload)
        db_session.commit()

        after = (
            db_session.query(CaseEvent)
            .filter(
                CaseEvent.case_id == "INT-2026-000002",
                CaseEvent.event_type == "REVIEWER_CONFLICT_DECLARED",
            )
            .count()
        )
        assert after == 1

        event = (
            db_session.query(CaseEvent)
            .filter(
                CaseEvent.case_id == "INT-2026-000002",
                CaseEvent.event_type == "REVIEWER_CONFLICT_DECLARED",
            )
            .one()
        )
        assert event.actor_role == "ACADEMIC_ADMIN"

    def test_writes_audit_log_for_update(self, db_session: Session):
        """update_conflict writes an AuditLog for the CaseReviewer UPDATE
        with non-null old_values (Requirement 13.4).

        Uses a fresh OPEN case so it does not depend on earlier test state
        or CLOSED-case guards.
        """
        session = db_session
        session.add(
            IntegrityCase(
                case_id="INT-2026-AUDITTEST",
                report_id="SIM-SUB-2026-000005-01",
                case_status="OPEN",
                priority="MEDIUM",
                opened_at=datetime(2026, 3, 1),
                closed_at=None,
            )
        )
        session.add(
            CaseReviewer(
                assignment_id=200,
                case_id="INT-2026-AUDITTEST",
                reviewer_id="REV-001",
                assignment_role="PRIMARY",
                assigned_at=datetime(2026, 3, 1, 12),
                conflict_status="PENDING",
            )
        )
        session.commit()

        before = (
            session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "CaseReviewer",
                AuditLog.action == "UPDATE",
            )
            .count()
        )

        payload = ConflictUpdate(
            conflict_status="CONFLICT",
            conflict_reason="Discovered conflict",
            actor_role="REVIEWER",
            actor_ref="REV-002",
        )
        update_conflict(session, "INT-2026-AUDITTEST", 200, payload)
        session.commit()

        after = (
            session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "CaseReviewer",
                AuditLog.action == "UPDATE",
            )
            .count()
        )
        assert after == before + 1

        log = (
            session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "CaseReviewer",
                AuditLog.action == "UPDATE",
            )
            .order_by(AuditLog.created_at.desc())
            .first()
        )
        assert log.old_values is not None  # UPDATE has old values
        assert log.old_values["conflict_status"] == "PENDING"
        assert log.new_values["conflict_status"] == "CONFLICT"
        assert log.actor_role == "REVIEWER"
        assert log.actor_ref == "REV-002"

    def test_404_for_unknown_case(self, db_session: Session):
        """Unknown case_id raises HTTP 404."""
        payload = ConflictUpdate(
            conflict_status="CONFLICT", actor_role="SYSTEM"
        )
        with pytest.raises(HTTPException) as exc_info:
            update_conflict(db_session, "INT-2026-999999", 1, payload)
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    def test_404_for_unknown_assignment(self, db_session: Session):
        """Unknown assignment_id raises HTTP 404."""
        payload = ConflictUpdate(
            conflict_status="CONFLICT", actor_role="SYSTEM"
        )
        with pytest.raises(HTTPException) as exc_info:
            update_conflict(db_session, "INT-2026-000001", 99999, payload)
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    def test_404_for_assignment_wrong_case(self, db_session: Session):
        """Assignment belonging to a different case raises HTTP 404."""
        payload = ConflictUpdate(
            conflict_status="CONFLICT", actor_role="SYSTEM"
        )
        # Assignment 2 belongs to INT-002, not INT-001
        with pytest.raises(HTTPException) as exc_info:
            update_conflict(db_session, "INT-2026-000001", 2, payload)
        assert exc_info.value.status_code == 404

    def test_422_for_closed_case(self, db_session: Session):
        """Declaring a conflict on a CLOSED case raises HTTP 422
        (Requirement 21.4).

        INT-003 is CLOSED. Assignment 4 belongs to it.
        """
        payload = ConflictUpdate(
            conflict_status="CONFLICT", actor_role="ACADEMIC_ADMIN"
        )
        with pytest.raises(HTTPException) as exc_info:
            update_conflict(db_session, "INT-2026-000003", 4, payload)
        assert exc_info.value.status_code == 422
        assert "CLOSED" in exc_info.value.detail

    def test_does_not_commit(self, db_session: Session):
        """update_conflict does not commit; rollback discards changes."""
        session = db_session
        session.add(
            IntegrityCase(
                case_id="INT-2026-CONFLICTROLLBACK",
                report_id="SIM-SUB-2026-000006-01",
                case_status="OPEN",
                priority="LOW",
                opened_at=datetime(2026, 3, 1),
                closed_at=None,
            )
        )
        session = db_session
        session.add(
            CaseReviewer(
                assignment_id=100,
                case_id="INT-2026-CONFLICTROLLBACK",
                reviewer_id="REV-001",
                assignment_role="PRIMARY",
                assigned_at=datetime(2026, 3, 1, 12),
                conflict_status="PENDING",
            )
        )
        session.commit()

        payload = ConflictUpdate(
            conflict_status="CONFLICT", actor_role="SYSTEM"
        )
        update_conflict(session, "INT-2026-CONFLICTROLLBACK", 100, payload)

        session.rollback()

        assignment = session.get(CaseReviewer, 100)
        assert assignment.conflict_status == "PENDING"
        assert assignment.unassigned_at is None


# ── get_reviewers tests ──────────────────────────────────────────────────────


class TestGetReviewers:
    """Tests for get_reviewers() — Requirement 9.6."""

    def test_returns_active_reviewers_only(self, db_session: Session):
        """get_reviewers returns only ACTIVE reviewers (Requirement 9.6)."""
        result = get_reviewers(db_session, page=1, page_size=20)
        assert isinstance(result, PaginatedReviewers)
        assert result.total_count == 2  # REV-001 and REV-002 are ACTIVE
        assert len(result.items) == 2
        reviewer_ids = {r.reviewer_id for r in result.items}
        assert reviewer_ids == {"REV-001", "REV-002"}
        # REV-003 is INACTIVE and should not be present
        assert "REV-003" not in reviewer_ids

    def test_pagination_first_page(self, db_session: Session):
        """Page 1 with page_size=1 returns 1 item."""
        result = get_reviewers(db_session, page=1, page_size=1)
        assert result.total_count == 2
        assert len(result.items) == 1
        assert result.page == 1
        assert result.page_size == 1

    def test_pagination_second_page(self, db_session: Session):
        """Page 2 with page_size=1 returns the remaining 1 item."""
        result = get_reviewers(db_session, page=2, page_size=1)
        assert result.total_count == 2
        assert len(result.items) == 1
        assert result.page == 2

    def test_pagination_empty_page_beyond_data(self, db_session: Session):
        """A page beyond the data range returns an empty items list."""
        result = get_reviewers(db_session, page=10, page_size=10)
        assert result.total_count == 2
        assert len(result.items) == 0

    def test_reviewer_out_fields(self, db_session: Session):
        """Each item has the expected ReviewerOut fields."""
        result = get_reviewers(db_session, page=1, page_size=20)
        reviewer = result.items[0]
        assert isinstance(reviewer, ReviewerOut)
        assert hasattr(reviewer, "reviewer_id")
        assert hasattr(reviewer, "full_name")
        assert hasattr(reviewer, "email")
        assert hasattr(reviewer, "reviewer_role")
        assert hasattr(reviewer, "status")
        assert reviewer.status == "ACTIVE"

    def test_pagination_envelope_complete(self, db_session: Session):
        """The response envelope has total_count, page, and page_size."""
        result = get_reviewers(db_session, page=1, page_size=20)
        assert result.total_count is not None
        assert result.page is not None
        assert result.page_size is not None
        assert len(result.items) <= result.page_size
