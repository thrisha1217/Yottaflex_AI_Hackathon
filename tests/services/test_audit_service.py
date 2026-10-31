"""
tests/services/test_audit_service.py

Verification tests for backend/services/audit_service.py.

Uses an in-memory SQLite database so no MySQL instance is needed. Only the
AuditLog and CaseEvent tables are created; SQLite does not enforce foreign
keys by default, so the CaseEvent FK to IntegrityCase is satisfied without
populating that table.

A compile hook renders ``BigInteger`` as ``INTEGER`` for the SQLite dialect so
that the primary-key columns autoincrement (SQLite only auto-generates
``INTEGER PRIMARY KEY``). Production stays on MySQL where ``BIGINT`` is correct.

Validates: Requirements 13.4, 13.5
"""

import os

# Point the app's DATABASE_URL at a throwaway SQLite file BEFORE importing any
# backend module. The engine created in backend.database is lazy (it never
# connects and never creates the file); we only need the import to succeed
# without the mysql-connector dependency so we can reach Base + the models.
os.environ.setdefault("DATABASE_URL", "sqlite:///./_audit_test_unused.db")

from datetime import datetime

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

# SQLite only auto-generates a primary key for a column declared exactly as
# "INTEGER PRIMARY KEY". The models use BigInteger (correct for MySQL), which
# SQLite renders as BIGINT and therefore does NOT autoincrement — inserts fail
# with NOT NULL on the PK. Render BigInteger as INTEGER for the SQLite dialect
# only; this is a test-only concern and does not touch production (MySQL).
@compiles(BigInteger, "sqlite")
def _big_int_as_integer_sqlite(element, compiler, **kw):  # noqa: ARG001
    return "INTEGER"

# ── Pull in Base and both target models ──────────────────────────────────────
from backend.database import Base
from backend.models.audit_log import AuditLog
from backend.models.case_event import CaseEvent

# We need to import all models that share the same Base metadata so that
# create_all can resolve cross-table FK references.  Rather than standing up
# the whole MySQL schema we patch CaseEvent's FK at the SQLite level below.
from backend.services.audit_service import (
    insert_case_event,
    log_insert,
    log_update,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def db_session():
    """
    Module-scoped in-memory SQLite session.

    SQLite doesn't enforce FK constraints by default, so the CaseEvent FK
    to IntegrityCase.case_id works without populating that table.
    We create *only* AuditLog and CaseEvent to keep the test self-contained.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Create just the two tables we exercise
    AuditLog.__table__.create(engine)
    CaseEvent.__table__.create(engine)

    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestSession()

    yield session

    session.close()
    engine.dispose()


# ── log_insert tests ─────────────────────────────────────────────────────────


def test_log_insert_creates_audit_log_row(db_session: Session):
    """log_insert should add exactly one AuditLog row."""
    before_count = db_session.query(AuditLog).count()

    log_insert(
        db=db_session,
        entity_type="IntegrityCase",
        entity_id="INT-2026-000001",
        new_values={"case_status": "OPEN"},
        actor_role="SYSTEM",
    )
    db_session.commit()

    after_count = db_session.query(AuditLog).count()
    assert after_count == before_count + 1


def test_log_insert_action_is_INSERT(db_session: Session):
    """AuditLog row from log_insert must have action='INSERT'."""
    log_insert(
        db=db_session,
        entity_type="EvidenceItem",
        entity_id="EVD-000001",
        new_values={"evidence_type": "DOCUMENT"},
        actor_role="REVIEWER",
    )
    db_session.commit()

    row = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == "EVD-000001")
        .one()
    )
    assert row.action == "INSERT"


def test_log_insert_old_values_is_none(db_session: Session):
    """INSERT audit rows must have old_values = NULL."""
    log_insert(
        db=db_session,
        entity_type="Decision",
        entity_id="DEC-001",
        new_values={"decision_outcome": "VIOLATION"},
        actor_role="REVIEWER",
        actor_ref="REV-001",
    )
    db_session.commit()

    row = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == "DEC-001")
        .one()
    )
    assert row.old_values is None


def test_log_insert_new_values_persisted(db_session: Session):
    """new_values dict must be retrievable from the database."""
    payload = {"appeal_status": "SUBMITTED", "learner_id": "LRN-001"}
    log_insert(
        db=db_session,
        entity_type="Appeal",
        entity_id="APL-000001",
        new_values=payload,
        actor_role="SYSTEM",
    )
    db_session.commit()

    row = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == "APL-000001")
        .one()
    )
    assert row.new_values == payload


def test_log_insert_stores_actor_role_and_optional_ref(db_session: Session):
    """actor_role and actor_ref are persisted correctly."""
    log_insert(
        db=db_session,
        entity_type="CaseReviewer",
        entity_id="42",
        new_values={"assignment_role": "PRIMARY"},
        actor_role="ACADEMIC_ADMIN",
        actor_ref="REV-005",
    )
    db_session.commit()

    row = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == "42")
        .one()
    )
    assert row.actor_role == "ACADEMIC_ADMIN"
    assert row.actor_ref == "REV-005"


def test_log_insert_actor_ref_defaults_to_none(db_session: Session):
    """actor_ref defaults to None when not supplied."""
    log_insert(
        db=db_session,
        entity_type="AppealReview",
        entity_id="ARV-001",
        new_values={"outcome": "UPHELD"},
        actor_role="SYSTEM",
    )
    db_session.commit()

    row = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == "ARV-001")
        .one()
    )
    assert row.actor_ref is None


def test_log_insert_created_at_is_recent(db_session: Session):
    """created_at must be a datetime and within a few seconds of now."""
    before = datetime.utcnow()
    log_insert(
        db=db_session,
        entity_type="IntegrityCase",
        entity_id="INT-2026-999999",
        new_values={"case_status": "OPEN"},
        actor_role="SYSTEM",
    )
    db_session.commit()
    after = datetime.utcnow()

    row = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == "INT-2026-999999")
        .one()
    )
    assert isinstance(row.created_at, datetime)
    assert before <= row.created_at <= after


def test_log_insert_entity_type_stored(db_session: Session):
    """entity_type must survive the round-trip to the database."""
    log_insert(
        db=db_session,
        entity_type="EvidenceItem",
        entity_id="EVD-TYPECHECK",
        new_values={"is_material": True},
        actor_role="REVIEWER",
    )
    db_session.commit()

    row = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == "EVD-TYPECHECK")
        .one()
    )
    assert row.entity_type == "EvidenceItem"


# ── log_update tests ──────────────────────────────────────────────────────────


def test_log_update_creates_audit_log_row(db_session: Session):
    """log_update should add exactly one AuditLog row."""
    before_count = db_session.query(AuditLog).count()

    log_update(
        db=db_session,
        entity_type="IntegrityCase",
        entity_id="INT-2026-000002",
        old_values={"case_status": "OPEN"},
        new_values={"case_status": "UNDER_REVIEW"},
        actor_role="REVIEWER",
    )
    db_session.commit()

    after_count = db_session.query(AuditLog).count()
    assert after_count == before_count + 1


def test_log_update_action_is_UPDATE(db_session: Session):
    """AuditLog row from log_update must have action='UPDATE'."""
    log_update(
        db=db_session,
        entity_type="Appeal",
        entity_id="APL-000002",
        old_values={"appeal_status": "SUBMITTED"},
        new_values={"appeal_status": "UNDER_REVIEW"},
        actor_role="ACADEMIC_ADMIN",
    )
    db_session.commit()

    row = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == "APL-000002")
        .one()
    )
    assert row.action == "UPDATE"


def test_log_update_old_values_is_non_null(db_session: Session):
    """UPDATE audit rows must carry a non-null old_values dict."""
    old = {"case_status": "UNDER_REVIEW"}
    log_update(
        db=db_session,
        entity_type="IntegrityCase",
        entity_id="INT-2026-000003",
        old_values=old,
        new_values={"case_status": "DECIDED"},
        actor_role="REVIEWER",
        actor_ref="REV-002",
    )
    db_session.commit()

    row = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == "INT-2026-000003")
        .one()
    )
    assert row.old_values is not None
    assert row.old_values == old


def test_log_update_new_values_persisted(db_session: Session):
    """new_values dict must be retrievable from the database after an update."""
    new = {"case_status": "CLOSED", "closed_at": "2026-06-01T00:00:00"}
    log_update(
        db=db_session,
        entity_type="IntegrityCase",
        entity_id="INT-2026-000004",
        old_values={"case_status": "DECIDED"},
        new_values=new,
        actor_role="SYSTEM",
    )
    db_session.commit()

    row = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == "INT-2026-000004")
        .one()
    )
    assert row.new_values == new


def test_log_update_stores_actor_ref(db_session: Session):
    """actor_ref is persisted for UPDATE logs."""
    log_update(
        db=db_session,
        entity_type="CaseReviewer",
        entity_id="99",
        old_values={"conflict_status": "NONE"},
        new_values={"conflict_status": "CONFLICT"},
        actor_role="ACADEMIC_ADMIN",
        actor_ref="REV-007",
    )
    db_session.commit()

    row = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == "99")
        .one()
    )
    assert row.actor_ref == "REV-007"


def test_log_update_created_at_is_recent(db_session: Session):
    """created_at for UPDATE audit must be a recent datetime."""
    before = datetime.utcnow()
    log_update(
        db=db_session,
        entity_type="Decision",
        entity_id="DEC-002",
        old_values={"is_final": False},
        new_values={"is_final": True},
        actor_role="REVIEWER",
    )
    db_session.commit()
    after = datetime.utcnow()

    row = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == "DEC-002")
        .one()
    )
    assert isinstance(row.created_at, datetime)
    assert before <= row.created_at <= after


# ── insert_case_event tests ───────────────────────────────────────────────────


def test_insert_case_event_creates_row(db_session: Session):
    """insert_case_event should add exactly one CaseEvent row."""
    before_count = db_session.query(CaseEvent).count()

    insert_case_event(
        db=db_session,
        case_id="INT-2026-000010",
        event_type="CASE_CREATED",
        actor_role="SYSTEM",
    )
    db_session.commit()

    after_count = db_session.query(CaseEvent).count()
    assert after_count == before_count + 1


def test_insert_case_event_fields_persisted(db_session: Session):
    """All provided fields are stored and retrievable."""
    insert_case_event(
        db=db_session,
        case_id="INT-2026-000011",
        event_type="STATUS_CHANGED",
        actor_role="REVIEWER",
        prev_status="OPEN",
        new_status="UNDER_REVIEW",
        details={"comment": "Initial triage complete"},
        actor_ref="REV-003",
    )
    db_session.commit()

    row = (
        db_session.query(CaseEvent)
        .filter(
            CaseEvent.case_id == "INT-2026-000011",
            CaseEvent.event_type == "STATUS_CHANGED",
        )
        .one()
    )
    assert row.case_id == "INT-2026-000011"
    assert row.event_type == "STATUS_CHANGED"
    assert row.actor_role == "REVIEWER"
    assert row.actor_ref == "REV-003"
    assert row.previous_status == "OPEN"
    assert row.new_status == "UNDER_REVIEW"
    assert row.event_details == {"comment": "Initial triage complete"}


def test_insert_case_event_occurred_at_is_recent(db_session: Session):
    """occurred_at must be a datetime stamped at insertion time."""
    before = datetime.utcnow()
    insert_case_event(
        db=db_session,
        case_id="INT-2026-000012",
        event_type="DECISION_RECORDED",
        actor_role="REVIEWER",
    )
    db_session.commit()
    after = datetime.utcnow()

    row = (
        db_session.query(CaseEvent)
        .filter(
            CaseEvent.case_id == "INT-2026-000012",
            CaseEvent.event_type == "DECISION_RECORDED",
        )
        .one()
    )
    assert isinstance(row.occurred_at, datetime)
    assert before <= row.occurred_at <= after


def test_insert_case_event_optional_fields_default_to_none(db_session: Session):
    """prev_status, new_status, details, and actor_ref default to None."""
    insert_case_event(
        db=db_session,
        case_id="INT-2026-000013",
        event_type="EVIDENCE_ADDED",
        actor_role="REVIEWER",
    )
    db_session.commit()

    row = (
        db_session.query(CaseEvent)
        .filter(
            CaseEvent.case_id == "INT-2026-000013",
            CaseEvent.event_type == "EVIDENCE_ADDED",
        )
        .one()
    )
    assert row.previous_status is None
    assert row.new_status is None
    assert row.event_details is None
    assert row.actor_ref is None


def test_insert_case_event_multiple_events_same_case(db_session: Session):
    """Multiple events for the same case_id are all stored individually."""
    case_id = "INT-2026-000020"

    for event_type in ("CASE_CREATED", "REVIEWER_ASSIGNED", "DECISION_RECORDED"):
        insert_case_event(
            db=db_session,
            case_id=case_id,
            event_type=event_type,
            actor_role="SYSTEM",
        )
    db_session.commit()

    rows = (
        db_session.query(CaseEvent)
        .filter(CaseEvent.case_id == case_id)
        .all()
    )
    event_types = {r.event_type for r in rows}
    assert {"CASE_CREATED", "REVIEWER_ASSIGNED", "DECISION_RECORDED"} == event_types


# ── No-commit contract tests ──────────────────────────────────────────────────


def test_log_insert_does_not_commit(db_session: Session):
    """log_insert must not commit; changes visible only after caller commits."""
    # Flush pending changes from prior tests
    db_session.commit()

    log_insert(
        db=db_session,
        entity_type="IntegrityCase",
        entity_id="UNCOMMITTED-INSERT",
        new_values={"case_status": "OPEN"},
        actor_role="SYSTEM",
    )

    # Roll back without committing — the row must disappear
    db_session.rollback()

    count = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == "UNCOMMITTED-INSERT")
        .count()
    )
    assert count == 0, "log_insert should not auto-commit; row must not persist after rollback"


def test_log_update_does_not_commit(db_session: Session):
    """log_update must not commit; changes lost on rollback."""
    db_session.commit()

    log_update(
        db=db_session,
        entity_type="IntegrityCase",
        entity_id="UNCOMMITTED-UPDATE",
        old_values={"case_status": "OPEN"},
        new_values={"case_status": "DECIDED"},
        actor_role="REVIEWER",
    )

    db_session.rollback()

    count = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == "UNCOMMITTED-UPDATE")
        .count()
    )
    assert count == 0, "log_update should not auto-commit; row must not persist after rollback"


def test_insert_case_event_does_not_commit(db_session: Session):
    """insert_case_event must not commit; CaseEvent row lost on rollback."""
    db_session.commit()

    insert_case_event(
        db=db_session,
        case_id="INT-2026-ROLLBACK",
        event_type="CASE_CREATED",
        actor_role="SYSTEM",
    )

    db_session.rollback()

    count = (
        db_session.query(CaseEvent)
        .filter(CaseEvent.case_id == "INT-2026-ROLLBACK")
        .count()
    )
    assert count == 0, "insert_case_event should not auto-commit; row must not persist after rollback"
