"""
tests/services/test_evidence_service.py

Service-level tests for the evidence management operations in
backend/services/evidence_service.py:
    add_evidence, get_evidence

Uses an in-memory SQLite database so no MySQL instance is needed.

Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.6
"""

import os

# Point the app's DATABASE_URL at a throwaway SQLite file BEFORE importing any
# backend module. The engine created in backend.database is lazy and never
# connects, so the import succeeds without the mysql-connector dependency.
os.environ.setdefault("DATABASE_URL", "sqlite:///./_evidence_test_unused.db")

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
from backend.models.evidence_item import EvidenceItem
from backend.models.integrity_case import IntegrityCase
from backend.models.integrity_rule import IntegrityRule
from backend.models.learner import Learner
from backend.models.reviewer import Reviewer
from backend.models.similarity_report import SimilarityReport
from backend.models.submission import Submission
from backend.schemas.evidence import EvidenceItemCreate, EvidenceItemOut
from backend.services.evidence_service import add_evidence, get_evidence


# ── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def db_session():
    """
    Module-scoped in-memory SQLite session with test data pre-loaded.

    Data set:
      * 1 Learner, 1 Assessment, 1 IntegrityRule
      * 2 Reviewers (ACTIVE)
      * 4 Submissions + SimilarityReports
      * 4 IntegrityCases:
          INT-001: OPEN
          INT-002: UNDER_REVIEW
          INT-003: CLOSED (for is_material=False testing)
          INT-004: OPEN (no evidence, for empty-list testing)
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
            EvidenceItem.__table__,
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
    for rid, role in [("REV-001", "INSTRUCTOR"), ("REV-002", "ACADEMIC_ADMIN")]:
        session.add(
            Reviewer(
                reviewer_id=rid,
                full_name=f"Reviewer {rid[-3:]}",
                email=f"{rid.lower()}@test.edu",
                reviewer_role=role,
                status="ACTIVE",
                created_at=datetime(2026, 1, 1),
            )
        )

    # ── Submissions + Reports ────────────────────────────────────────────
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
        ("INT-2026-000003", "SIM-SUB-2026-000003-01", "CLOSED", "LOW",
         datetime(2026, 2, 17, 2), datetime(2026, 2, 25)),
        ("INT-2026-000004", "SIM-SUB-2026-000004-01", "OPEN", "LOW",
         datetime(2026, 2, 18), None),
        ("INT-2026-000005", "SIM-SUB-2026-000005-01", "OPEN", "LOW",
         datetime(2026, 2, 19), None),
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

    # ── Case Events ──────────────────────────────────────────────────────
    for case_id, etype, occurred_at in [
        ("INT-2026-000001", "CASE_CREATED", datetime(2026, 2, 17, 0)),
        ("INT-2026-000002", "CASE_CREATED", datetime(2026, 2, 17, 1)),
        ("INT-2026-000003", "CASE_CREATED", datetime(2026, 2, 17, 2)),
        ("INT-2026-000004", "CASE_CREATED", datetime(2026, 2, 18, 0)),
        ("INT-2026-000005", "CASE_CREATED", datetime(2026, 2, 19, 0)),
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


# ── add_evidence tests ───────────────────────────────────────────────────────


class TestAddEvidence:
    """Tests for add_evidence() — Requirements 10.1, 10.3, 10.4, 10.6."""

    def test_adds_evidence_to_open_case(self, db_session: Session):
        """Adding evidence to an OPEN case returns EvidenceItemOut with
        is_material=True (Requirement 10.1).
        """
        payload = EvidenceItemCreate(
            evidence_type="SIMILARITY_MATCH",
            description="Highlighted match in paragraph 3",
            evidence_reference="SIM-SUB-2026-000001-01#match-005",
            added_by_role="REVIEWER",
            added_by_ref="REV-001",
            actor_role="REVIEWER",
        )
        result = add_evidence(db_session, "INT-2026-000001", payload)
        assert isinstance(result, EvidenceItemOut)
        assert result.case_id == "INT-2026-000001"
        assert result.evidence_type == "SIMILARITY_MATCH"
        assert result.description == "Highlighted match in paragraph 3"
        assert result.evidence_reference == "SIM-SUB-2026-000001-01#match-005"
        assert result.added_by_role == "REVIEWER"
        assert result.added_by_ref == "REV-001"
        assert result.is_material is True
        assert result.evidence_id.startswith("EVD-")
        db_session.commit()

    def test_evidence_id_format_sequential(self, db_session: Session):
        """evidence_id is generated as EVD-{count+1:06d}."""
        # INT-001 already has one evidence item from the previous test
        count_before = db_session.query(EvidenceItem).count()

        payload = EvidenceItemCreate(
            evidence_type="DOCUMENT",
            description="Email correspondence",
            added_by_role="INSTRUCTOR",
            added_by_ref="REV-002",
            actor_role="INSTRUCTOR",
        )
        result = add_evidence(db_session, "INT-2026-000001", payload)
        expected_id = f"EVD-{count_before + 1:06d}"
        assert result.evidence_id == expected_id
        db_session.commit()

    def test_post_decision_evidence_is_non_material(self, db_session: Session):
        """Property 23: Post-decision evidence is non-material — adding
        evidence to a CLOSED case sets is_material=False (Requirement 10.4).

        Validates: Requirements 10.4
        """
        payload = EvidenceItemCreate(
            evidence_type="STUDENT_EXPLANATION",
            description="Late submission explanation",
            added_by_role="REVIEWER",
            added_by_ref="REV-002",
            actor_role="REVIEWER",
        )
        result = add_evidence(db_session, "INT-2026-000003", payload)
        assert isinstance(result, EvidenceItemOut)
        assert result.case_id == "INT-2026-000003"
        assert result.is_material is False
        db_session.commit()

    def test_404_for_unknown_case(self, db_session: Session):
        """Unknown case_id raises HTTP 404 (Requirement 10.6)."""
        payload = EvidenceItemCreate(
            evidence_type="QUOTATION",
            description="Direct quotation found",
            added_by_role="REVIEWER",
            actor_role="SYSTEM",
        )
        with pytest.raises(HTTPException) as exc_info:
            add_evidence(db_session, "INT-2026-999999", payload)
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    def test_inserts_evidence_added_case_event(self, db_session: Session):
        """add_evidence inserts an EVIDENCE_ADDED CaseEvent (Requirement 10.3)."""
        before = (
            db_session.query(CaseEvent)
            .filter(
                CaseEvent.case_id == "INT-2026-000002",
                CaseEvent.event_type == "EVIDENCE_ADDED",
            )
            .count()
        )
        assert before == 0

        payload = EvidenceItemCreate(
            evidence_type="TEMPLATE",
            description="Assignment template comparison",
            added_by_role="REVIEWER",
            added_by_ref="REV-001",
            actor_role="REVIEWER",
        )
        add_evidence(db_session, "INT-2026-000002", payload)
        db_session.commit()

        after = (
            db_session.query(CaseEvent)
            .filter(
                CaseEvent.case_id == "INT-2026-000002",
                CaseEvent.event_type == "EVIDENCE_ADDED",
            )
            .count()
        )
        assert after == 1

        event = (
            db_session.query(CaseEvent)
            .filter(
                CaseEvent.case_id == "INT-2026-000002",
                CaseEvent.event_type == "EVIDENCE_ADDED",
            )
            .one()
        )
        assert event.actor_role == "REVIEWER"
        assert event.actor_ref == "REV-001"

    def test_writes_audit_log_for_insert(self, db_session: Session):
        """add_evidence writes an AuditLog for the EvidenceItem INSERT
        (Requirement 13.4).
        """
        before = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "EvidenceItem",
                AuditLog.action == "INSERT",
            )
            .count()
        )

        payload = EvidenceItemCreate(
            evidence_type="OTHER",
            description="Witness statement",
            added_by_role="ACADEMIC_ADMIN",
            added_by_ref="REV-002",
            actor_role="ACADEMIC_ADMIN",
        )
        add_evidence(db_session, "INT-2026-000004", payload)
        db_session.commit()

        after = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "EvidenceItem",
                AuditLog.action == "INSERT",
            )
            .count()
        )
        assert after == before + 1

        log = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "EvidenceItem",
                AuditLog.action == "INSERT",
            )
            .order_by(AuditLog.created_at.desc())
            .first()
        )
        assert log.old_values is None  # INSERT has no old values
        assert log.new_values is not None
        assert log.new_values["case_id"] == "INT-2026-000004"
        assert log.new_values["evidence_type"] == "OTHER"
        assert log.new_values["is_material"] is True  # OPEN case
        assert log.actor_role == "ACADEMIC_ADMIN"
        assert log.actor_ref == "REV-002"

    def test_does_not_commit(self, db_session: Session):
        """add_evidence does not commit; rollback discards the new record."""
        payload = EvidenceItemCreate(
            evidence_type="SIMILARITY_MATCH",
            description="Should be rolled back",
            added_by_role="REVIEWER",
            actor_role="SYSTEM",
        )
        add_evidence(db_session, "INT-2026-000004", payload)
        db_session.rollback()

        # The evidence item should not exist after rollback
        count = (
            db_session.query(EvidenceItem)
            .filter(
                EvidenceItem.case_id == "INT-2026-000004",
                EvidenceItem.description == "Should be rolled back",
            )
            .count()
        )
        assert count == 0


# ── get_evidence tests ───────────────────────────────────────────────────────


class TestGetEvidence:
    """Tests for get_evidence() — Requirements 10.2, 10.6."""

    def test_returns_evidence_ordered_by_added_at(self, db_session: Session):
        """get_evidence returns evidence ordered by added_at ascending
        (Requirement 10.2).

        INT-001 has two evidence items from the add_evidence tests above.
        """
        result = get_evidence(db_session, "INT-2026-000001")
        assert len(result) >= 1
        # Verify ordering by added_at ascending
        added_ats = [e.added_at for e in result]
        assert added_ats == sorted(added_ats)
        for item in result:
            assert isinstance(item, EvidenceItemOut)
            assert item.case_id == "INT-2026-000001"

    def test_404_for_unknown_case(self, db_session: Session):
        """Unknown case_id raises HTTP 404 (Requirement 10.6)."""
        with pytest.raises(HTTPException) as exc_info:
            get_evidence(db_session, "INT-2026-999999")
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    def test_returns_empty_list_for_case_with_no_evidence(
        self, db_session: Session
    ):
        """A case with no evidence returns an empty list (not 404)."""
        # INT-2026-000005 is a dedicated case that never receives evidence
        result = get_evidence(db_session, "INT-2026-000005")
        assert isinstance(result, list)
        assert len(result) == 0

    def test_out_fields_complete(self, db_session: Session):
        """Each EvidenceItemOut has all expected fields."""
        result = get_evidence(db_session, "INT-2026-000001")
        if result:
            item = result[0]
            assert hasattr(item, "evidence_id")
            assert hasattr(item, "case_id")
            assert hasattr(item, "evidence_type")
            assert hasattr(item, "description")
            assert hasattr(item, "evidence_reference")
            assert hasattr(item, "added_by_role")
            assert hasattr(item, "added_by_ref")
            assert hasattr(item, "added_at")
            assert hasattr(item, "is_material")
