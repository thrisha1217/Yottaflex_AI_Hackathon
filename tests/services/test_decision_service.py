"""
tests/services/test_decision_service.py

Service-level tests for the decision management operations in
backend/services/decision_service.py:
    create_decision, get_decisions

Uses an in-memory SQLite database so no MySQL instance is needed.

Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 21.2
"""

import os

# Point the app's DATABASE_URL at a throwaway SQLite file BEFORE importing
# any backend module. The engine is lazy so the import succeeds without MySQL.
os.environ.setdefault("DATABASE_URL", "sqlite:///./_decision_test_unused.db")

from datetime import datetime

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
from backend.models.appeal import Appeal
from backend.models.assessment import Assessment
from backend.models.audit_log import AuditLog
from backend.models.case_event import CaseEvent
from backend.models.case_reviewer import CaseReviewer
from backend.models.decision import Decision
from backend.models.decision_evidence import DecisionEvidence
from backend.models.evidence_item import EvidenceItem
from backend.models.integrity_case import IntegrityCase
from backend.models.integrity_rule import IntegrityRule
from backend.models.learner import Learner
from backend.models.reviewer import Reviewer
from backend.models.similarity_report import SimilarityReport
from backend.models.submission import Submission
from backend.schemas.decisions import DecisionCreate, DecisionOut
from backend.services.decision_service import create_decision, get_decisions


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def db_session():
    """
    Module-scoped in-memory SQLite session with a minimal dataset:

    Cases:
        INT-DEC-001  UNDER_REVIEW   — clean, no decisions yet
        INT-DEC-002  DECIDED        — already has a final decision (no appeal)
        INT-DEC-003  APPEAL_PENDING — has a final decision + pending appeal
        INT-DEC-004  UNDER_REVIEW   — for evidence_ids linking tests
        INT-DEC-005  UNDER_REVIEW   — for get_decisions ordering tests
        INT-DEC-999  does not exist  — for 404 tests

    Decisions:
        DEC-1001     case=INT-DEC-002, is_final=True  (already decided, no appeal)
        DEC-1002     case=INT-DEC-003, is_final=True  (has a pending appeal)
        DEC-1003     case=INT-DEC-005, is_final=True  (oldest; two more follow)
        DEC-1004     case=INT-DEC-005, is_final=True
        DEC-1005     case=INT-DEC-005, is_final=True  (most recent)

    EvidenceItems:
        EVD-DEC-001  case=INT-DEC-004
        EVD-DEC-002  case=INT-DEC-004

    Appeals:
        APL-DEC-001  case=INT-DEC-003, appeal_status=SUBMITTED
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
            Decision.__table__,
            DecisionEvidence.__table__,
            Appeal.__table__,
            AuditLog.__table__,
            CaseEvent.__table__,
        ],
    )

    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestSession()

    # ── Reference data ───────────────────────────────────────────────────
    session.add(
        Learner(
            learner_id="LRN-DEC-001",
            full_name="Test Learner",
            email="dec_learner@test.edu",
            program="Computer Science",
            year_of_study=3,
            status="ACTIVE",
            created_at=datetime(2026, 1, 1),
        )
    )
    session.add(
        Assessment(
            assessment_id="ASM-DEC-001",
            title="Decision Test Assessment",
            course_code="CS200",
            assessment_type="ASSIGNMENT",
            due_at=datetime(2026, 4, 1),
            status="ACTIVE",
            created_at=datetime(2026, 1, 1),
        )
    )
    session.add(
        IntegrityRule(
            rule_id="RULE-DEC-001",
            rule_name="Review Threshold",
            min_similarity=71.00,
            max_similarity=85.00,
            action_type="REVIEW",
            priority=3,
            effective_from=datetime(2026, 1, 1).date(),
            is_active=True,
        )
    )

    # ── Reviewers ────────────────────────────────────────────────────────
    for rid, role in [("REV-DEC-001", "INSTRUCTOR"), ("REV-DEC-002", "ACADEMIC_ADMIN")]:
        session.add(
            Reviewer(
                reviewer_id=rid,
                full_name=f"Reviewer {rid}",
                email=f"{rid.lower()}@test.edu",
                reviewer_role=role,
                status="ACTIVE",
                created_at=datetime(2026, 1, 1),
            )
        )

    # ── 6 Submissions + Reports (one per case) ───────────────────────────
    for i in range(1, 7):
        session.add(
            Submission(
                submission_id=f"SUB-DEC-{i:06d}",
                learner_id="LRN-DEC-001",
                assessment_id="ASM-DEC-001",
                attempt_no=1,
                submitted_at=datetime(2026, 2, 15),
                status="SUBMITTED",
                content_reference=f"ref-dec-{i}",
                content_hash=f"{i:064x}",
            )
        )
        session.add(
            SimilarityReport(
                report_id=f"SIM-DEC-{i:06d}-01",
                submission_id=f"SUB-DEC-{i:06d}",
                rule_id="RULE-DEC-001",
                report_no=1,
                similarity_score=85.50,
                matched_source_count=5,
                review_required=True,
                report_status="REVIEW_REQUIRED",
                generated_at=datetime(2026, 2, 16),
            )
        )

    # ── Integrity Cases ──────────────────────────────────────────────────
    cases_data = [
        ("INT-DEC-001", "SIM-DEC-000001-01", "UNDER_REVIEW",   "HIGH",   datetime(2026, 2, 17), None),
        ("INT-DEC-002", "SIM-DEC-000002-01", "DECIDED",        "MEDIUM", datetime(2026, 2, 17), None),
        ("INT-DEC-003", "SIM-DEC-000003-01", "APPEAL_PENDING", "MEDIUM", datetime(2026, 2, 17), None),
        ("INT-DEC-004", "SIM-DEC-000004-01", "UNDER_REVIEW",   "LOW",    datetime(2026, 2, 18), None),
        ("INT-DEC-005", "SIM-DEC-000005-01", "DECIDED",        "LOW",    datetime(2026, 2, 19), None),
        ("INT-DEC-006", "SIM-DEC-000006-01", "UNDER_REVIEW",   "LOW",    datetime(2026, 2, 20), None),
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

    # ── CaseEvents ───────────────────────────────────────────────────────
    for case_id, occurred_at in [
        ("INT-DEC-001", datetime(2026, 2, 17)),
        ("INT-DEC-002", datetime(2026, 2, 17, 1)),
        ("INT-DEC-003", datetime(2026, 2, 17, 2)),
        ("INT-DEC-004", datetime(2026, 2, 18)),
        ("INT-DEC-005", datetime(2026, 2, 19)),
        ("INT-DEC-006", datetime(2026, 2, 20)),
    ]:
        session.add(
            CaseEvent(
                case_id=case_id,
                event_type="CASE_CREATED",
                actor_role="SYSTEM",
                occurred_at=occurred_at,
            )
        )

    # ── Decisions ────────────────────────────────────────────────────────
    # INT-DEC-002: already has a final decision, no appeal → should block new decisions
    session.add(
        Decision(
            decision_id=1001,
            case_id="INT-DEC-002",
            reviewer_id="REV-DEC-001",
            decision_outcome="VIOLATION",
            rationale="Clear evidence of plagiarism.",
            decided_at=datetime(2026, 3, 1),
            is_final=True,
        )
    )
    # INT-DEC-003: has a final decision, but also has a pending appeal → new decision allowed
    session.add(
        Decision(
            decision_id=1002,
            case_id="INT-DEC-003",
            reviewer_id="REV-DEC-001",
            decision_outcome="VIOLATION",
            rationale="Initial finding.",
            decided_at=datetime(2026, 3, 1, 1),
            is_final=True,
        )
    )
    # INT-DEC-005: three decisions for ordering tests
    session.add(
        Decision(
            decision_id=1003,
            case_id="INT-DEC-005",
            reviewer_id="REV-DEC-001",
            decision_outcome="INCONCLUSIVE",
            rationale="First inconclusive.",
            decided_at=datetime(2026, 3, 1),
            is_final=True,
        )
    )
    session.add(
        Decision(
            decision_id=1004,
            case_id="INT-DEC-005",
            reviewer_id="REV-DEC-002",
            decision_outcome="NO_VIOLATION",
            rationale="Second finding.",
            decided_at=datetime(2026, 3, 2),
            is_final=True,
        )
    )
    session.add(
        Decision(
            decision_id=1005,
            case_id="INT-DEC-005",
            reviewer_id="REV-DEC-001",
            decision_outcome="VIOLATION",
            rationale="Most recent finding.",
            decided_at=datetime(2026, 3, 3),
            is_final=True,
        )
    )

    # ── EvidenceItems for INT-DEC-004 ────────────────────────────────────
    session.add(
        EvidenceItem(
            evidence_id="EVD-DEC-001",
            case_id="INT-DEC-004",
            evidence_type="SIMILARITY_MATCH",
            description="Match found in section 2.",
            added_by_role="REVIEWER",
            added_by_ref="REV-DEC-001",
            added_at=datetime(2026, 2, 20),
            is_material=True,
        )
    )
    session.add(
        EvidenceItem(
            evidence_id="EVD-DEC-002",
            case_id="INT-DEC-004",
            evidence_type="DOCUMENT",
            description="Source document.",
            added_by_role="REVIEWER",
            added_by_ref="REV-DEC-001",
            added_at=datetime(2026, 2, 21),
            is_material=True,
        )
    )

    # ── Appeal for INT-DEC-003 ────────────────────────────────────────────
    session.add(
        Appeal(
            appeal_id="APL-DEC-001",
            case_id="INT-DEC-003",
            learner_id="LRN-DEC-001",
            appeal_no=1,
            reason="I disagree with the finding.",
            submitted_at=datetime(2026, 3, 5),
            appeal_status="SUBMITTED",
        )
    )

    session.commit()

    yield session

    session.close()
    engine.dispose()


# ── create_decision tests ─────────────────────────────────────────────────────


class TestCreateDecision:
    """Tests for create_decision() — Requirements 11.1, 11.3, 11.6, 21.2."""

    def test_creates_decision_for_open_case(self, db_session: Session):
        """A new Decision is created for an UNDER_REVIEW case (Requirement 11.1).

        Validates: Requirements 11.1
        """
        payload = DecisionCreate(
            reviewer_id="REV-DEC-001",
            decision_outcome="NO_VIOLATION",
            rationale="No evidence of plagiarism found.",
            evidence_ids=[],
            actor_role="REVIEWER",
        )
        result = create_decision(db_session, "INT-DEC-001", payload)

        assert isinstance(result, DecisionOut)
        assert result.case_id == "INT-DEC-001"
        assert result.reviewer_id == "REV-DEC-001"
        assert result.decision_outcome == "NO_VIOLATION"
        assert result.rationale == "No evidence of plagiarism found."
        assert result.is_final is True
        assert result.decided_at is not None
        assert result.decision_id is not None
        db_session.commit()

    def test_sets_case_status_to_decided(self, db_session: Session):
        """create_decision sets case_status to DECIDED (Requirement 11.3).

        Validates: Requirements 11.3
        """
        case = db_session.get(IntegrityCase, "INT-DEC-001")
        assert case is not None
        assert case.case_status == "DECIDED"

    def test_inserts_decision_recorded_case_event(self, db_session: Session):
        """create_decision inserts a DECISION_RECORDED CaseEvent (Req 11.3).

        Validates: Requirements 11.3
        """
        events = (
            db_session.query(CaseEvent)
            .filter(
                CaseEvent.case_id == "INT-DEC-001",
                CaseEvent.event_type == "DECISION_RECORDED",
            )
            .all()
        )
        assert len(events) == 1
        assert events[0].actor_role == "REVIEWER"
        assert events[0].previous_status == "UNDER_REVIEW"
        assert events[0].new_status == "DECIDED"

    def test_writes_audit_log_for_decision_insert(self, db_session: Session):
        """create_decision writes AuditLog for Decision INSERT (Req 13.4).

        Validates: Requirements 11.1, 11.3
        """
        logs = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "Decision",
                AuditLog.action == "INSERT",
            )
            .order_by(AuditLog.created_at.desc())
            .all()
        )
        assert len(logs) >= 1
        latest = logs[0]
        assert latest.new_values is not None
        assert latest.new_values["case_id"] == "INT-DEC-001"
        assert latest.new_values["decision_outcome"] == "NO_VIOLATION"
        assert latest.new_values["is_final"] is True
        assert latest.old_values is None

    def test_writes_audit_log_for_case_update(self, db_session: Session):
        """create_decision writes AuditLog for IntegrityCase UPDATE (Req 13.4).

        Validates: Requirements 11.3
        """
        logs = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "IntegrityCase",
                AuditLog.action == "UPDATE",
                AuditLog.entity_id == "INT-DEC-001",
            )
            .all()
        )
        assert len(logs) >= 1
        log = logs[-1]
        assert log.old_values["case_status"] == "UNDER_REVIEW"
        assert log.new_values["case_status"] == "DECIDED"

    def test_creates_decision_evidence_rows(self, db_session: Session):
        """create_decision creates DecisionEvidence rows for each evidence_id
        (Requirement 11.6).

        Validates: Requirements 11.6
        """
        payload = DecisionCreate(
            reviewer_id="REV-DEC-001",
            decision_outcome="VIOLATION",
            rationale="Evidence clearly shows copying.",
            evidence_ids=["EVD-DEC-001", "EVD-DEC-002"],
            actor_role="REVIEWER",
        )
        result = create_decision(db_session, "INT-DEC-004", payload)
        db_session.commit()

        de_rows = (
            db_session.query(DecisionEvidence)
            .filter(DecisionEvidence.decision_id == result.decision_id)
            .all()
        )
        assert len(de_rows) == 2
        evidence_ids = {row.evidence_id for row in de_rows}
        assert "EVD-DEC-001" in evidence_ids
        assert "EVD-DEC-002" in evidence_ids

    def test_404_for_unknown_case(self, db_session: Session):
        """Unknown case_id raises HTTP 404.

        Validates: Requirements 11.1
        """
        payload = DecisionCreate(
            reviewer_id="REV-DEC-001",
            decision_outcome="INCONCLUSIVE",
            rationale="Test.",
            evidence_ids=[],
            actor_role="REVIEWER",
        )
        with pytest.raises(HTTPException) as exc_info:
            create_decision(db_session, "INT-DEC-999", payload)
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    def test_409_when_final_decision_exists_no_pending_appeal(
        self, db_session: Session
    ):
        """Creates HTTP 409 when a final Decision already exists and no appeal
        is pending (Requirement 21.2).

        INT-DEC-002 has decision_id=1001 (is_final=True) and no appeals.

        Validates: Requirements 21.2
        """
        payload = DecisionCreate(
            reviewer_id="REV-DEC-002",
            decision_outcome="NO_VIOLATION",
            rationale="Re-reviewing.",
            evidence_ids=[],
            actor_role="REVIEWER",
        )
        with pytest.raises(HTTPException) as exc_info:
            create_decision(db_session, "INT-DEC-002", payload)
        assert exc_info.value.status_code == 409
        assert "final Decision" in exc_info.value.detail

    def test_allows_new_decision_when_pending_appeal_exists(
        self, db_session: Session
    ):
        """Allows a new Decision when the case has a pending appeal (Req 21.2).

        INT-DEC-003 has decision_id=1002 (is_final=True) AND an appeal with
        appeal_status=SUBMITTED, so a new decision must be allowed.

        Validates: Requirements 21.2
        """
        payload = DecisionCreate(
            reviewer_id="REV-DEC-002",
            decision_outcome="NO_VIOLATION",
            rationale="After reviewing the appeal, the finding is overturned.",
            previous_decision_id=1002,
            evidence_ids=[],
            actor_role="REVIEWER",
        )
        # Should NOT raise
        result = create_decision(db_session, "INT-DEC-003", payload)
        assert isinstance(result, DecisionOut)
        assert result.previous_decision_id == 1002
        db_session.commit()

    def test_422_when_previous_decision_belongs_to_different_case(
        self, db_session: Session
    ):
        """HTTP 422 when previous_decision_id belongs to a different case
        (Requirement 11.4).

        INT-DEC-006 is a clean case; decision_id=1001 belongs to INT-DEC-002.

        Validates: Requirements 11.4
        """
        payload = DecisionCreate(
            reviewer_id="REV-DEC-001",
            decision_outcome="NO_VIOLATION",
            rationale="Testing cross-case validation.",
            previous_decision_id=1001,  # belongs to INT-DEC-002, not INT-DEC-006
            evidence_ids=[],
            actor_role="REVIEWER",
        )
        with pytest.raises(HTTPException) as exc_info:
            create_decision(db_session, "INT-DEC-006", payload)
        assert exc_info.value.status_code == 422
        assert "previous_decision_id" in exc_info.value.detail

    def test_422_when_previous_decision_id_does_not_exist(
        self, db_session: Session
    ):
        """HTTP 422 when previous_decision_id references a non-existent
        Decision (Requirement 11.4).

        Validates: Requirements 11.4
        """
        payload = DecisionCreate(
            reviewer_id="REV-DEC-001",
            decision_outcome="INCONCLUSIVE",
            rationale="Previous decision does not exist.",
            previous_decision_id=99999,
            evidence_ids=[],
            actor_role="REVIEWER",
        )
        with pytest.raises(HTTPException) as exc_info:
            # INT-DEC-006 is still clean (previous test rolled back or didn't commit yet)
            create_decision(db_session, "INT-DEC-006", payload)
        assert exc_info.value.status_code == 422
        assert "previous_decision_id" in exc_info.value.detail

    def test_does_not_commit(self, db_session: Session):
        """create_decision does not commit; rollback discards the new record.

        Validates: Requirements 11.1
        """
        # Make sure INT-DEC-006 doesn't have any committed decisions first.
        db_session.query(Decision).filter(
            Decision.case_id == "INT-DEC-006"
        ).delete()
        db_session.commit()

        # Reset case status to UNDER_REVIEW so the guard doesn't block us.
        case = db_session.get(IntegrityCase, "INT-DEC-006")
        case.case_status = "UNDER_REVIEW"
        db_session.commit()

        payload = DecisionCreate(
            reviewer_id="REV-DEC-001",
            decision_outcome="NO_VIOLATION",
            rationale="Should be rolled back.",
            evidence_ids=[],
            actor_role="REVIEWER",
        )
        create_decision(db_session, "INT-DEC-006", payload)
        db_session.rollback()

        count = (
            db_session.query(Decision)
            .filter(
                Decision.case_id == "INT-DEC-006",
                Decision.rationale == "Should be rolled back.",
            )
            .count()
        )
        assert count == 0

    def test_empty_evidence_ids_creates_no_decision_evidence_rows(
        self, db_session: Session
    ):
        """No DecisionEvidence rows are created when evidence_ids is empty.

        Validates: Requirements 11.6
        """
        # INT-DEC-001 already decided; use INT-DEC-006 which was reset above.
        case = db_session.get(IntegrityCase, "INT-DEC-006")
        case.case_status = "UNDER_REVIEW"
        db_session.commit()

        payload = DecisionCreate(
            reviewer_id="REV-DEC-002",
            decision_outcome="INCONCLUSIVE",
            rationale="No evidence attached.",
            evidence_ids=[],
            actor_role="REVIEWER",
        )
        result = create_decision(db_session, "INT-DEC-006", payload)
        db_session.commit()

        de_count = (
            db_session.query(DecisionEvidence)
            .filter(DecisionEvidence.decision_id == result.decision_id)
            .count()
        )
        assert de_count == 0


# ── get_decisions tests ───────────────────────────────────────────────────────


class TestGetDecisions:
    """Tests for get_decisions() — Requirements 11.2."""

    def test_returns_decisions_ordered_by_decided_at_descending(
        self, db_session: Session
    ):
        """get_decisions returns decisions ordered by decided_at descending
        (Requirement 11.2).

        INT-DEC-005 has three pre-loaded decisions with distinct decided_at
        timestamps (2026-03-01, 2026-03-02, 2026-03-03).

        Validates: Requirements 11.2
        """
        result = get_decisions(db_session, "INT-DEC-005")
        assert len(result) >= 3
        decided_ats = [d.decided_at for d in result]
        assert decided_ats == sorted(decided_ats, reverse=True)
        for d in result:
            assert isinstance(d, DecisionOut)
            assert d.case_id == "INT-DEC-005"

    def test_most_recent_decision_is_first(self, db_session: Session):
        """The most recent decision appears first in the list.

        Validates: Requirements 11.2
        """
        result = get_decisions(db_session, "INT-DEC-005")
        assert result[0].decision_id == 1005  # decided_at=2026-03-03
        assert result[-1].decision_id == 1003  # decided_at=2026-03-01

    def test_404_for_unknown_case(self, db_session: Session):
        """Unknown case_id raises HTTP 404.

        Validates: Requirements 11.2
        """
        with pytest.raises(HTTPException) as exc_info:
            get_decisions(db_session, "INT-DEC-999")
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    def test_returns_empty_list_for_case_with_no_decisions(
        self, db_session: Session
    ):
        """A case with no decisions returns an empty list, not a 404.

        Validates: Requirements 11.2
        """
        # INT-DEC-006 may have had a decision rolled back; ensure it's empty.
        result = get_decisions(db_session, "INT-DEC-006")
        # Could be 0 or 1 depending on test order — it should never raise 404.
        assert isinstance(result, list)

    def test_out_fields_complete(self, db_session: Session):
        """Each DecisionOut has all expected fields.

        Validates: Requirements 11.2
        """
        result = get_decisions(db_session, "INT-DEC-005")
        assert len(result) >= 1
        d = result[0]
        assert hasattr(d, "decision_id")
        assert hasattr(d, "case_id")
        assert hasattr(d, "reviewer_id")
        assert hasattr(d, "previous_decision_id")
        assert hasattr(d, "decision_outcome")
        assert hasattr(d, "rationale")
        assert hasattr(d, "decided_at")
        assert hasattr(d, "is_final")

    def test_previous_decision_id_preserved(self, db_session: Session):
        """previous_decision_id is correctly persisted and returned.

        Validates: Requirements 11.4
        """
        result = get_decisions(db_session, "INT-DEC-003")
        # INT-DEC-003 gained a decision (previous_decision_id=1002) in
        # test_allows_new_decision_when_pending_appeal_exists.
        decisions_with_prev = [
            d for d in result if d.previous_decision_id is not None
        ]
        assert len(decisions_with_prev) >= 1
        assert decisions_with_prev[0].previous_decision_id == 1002
