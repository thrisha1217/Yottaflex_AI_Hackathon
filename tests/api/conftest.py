"""
tests/api/conftest.py

Shared fixtures for API-level integration tests.

Provides a ``client`` fixture that creates a FastAPI TestClient backed by an
in-memory SQLite database with seed data, and overrides the ``get_db``
dependency so every request uses the test session.

Validates: Requirements 8.1, 8.2, 8.3, 8.7
"""

import os

# Point the app's DATABASE_URL at a throwaway SQLite file BEFORE importing any
# backend module. The engine created in backend.database is lazy and never
# connects, so the import succeeds without the mysql-connector dependency.
os.environ.setdefault("DATABASE_URL", "sqlite:///./_api_test_unused.db")

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker


# Render BigInteger as INTEGER for SQLite so PK autoincrement works.
@compiles(BigInteger, "sqlite")
def _big_int_as_integer_sqlite(element, compiler, **kw):  # noqa: ARG001
    return "INTEGER"


from backend.database import Base, get_db
from backend.main import create_app
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


@pytest.fixture()
def db_session():
    """Function-scoped in-memory SQLite session with seed data for API tests."""
    # check_same_thread=False allows the TestClient (which runs endpoints in a
    # worker thread) to share the same connection as the test fixture.
    # StaticPool keeps a single connection alive so all threads see the same
    # in-memory database (SQLite :memory: is otherwise per-connection).
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

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
    # REV-003: INACTIVE reviewer for 422 guard testing (Requirement 21.3)
    session.add(
        Reviewer(
            reviewer_id="REV-003",
            full_name="Reviewer 3",
            email="reviewer3@test.edu",
            reviewer_role="REVIEWER",
            status="INACTIVE",
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


@pytest.fixture()
def client(db_session: Session):
    """FastAPI TestClient with the get_db dependency overridden to use the
    in-memory test session."""
    app = create_app()

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass  # session lifecycle managed by db_session fixture

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
