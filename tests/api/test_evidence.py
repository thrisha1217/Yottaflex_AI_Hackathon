"""
tests/api/test_evidence.py

API-level integration tests for the Evidence router
(backend/routers/evidence.py).

Covers:
    POST /cases/{case_id}/evidence  — add evidence; HTTP 201
    GET  /cases/{case_id}/evidence  — list evidence ordered by added_at
    DELETE /cases/{case_id}/evidence — HTTP 405 (immutable)
    PUT    /cases/{case_id}/evidence — HTTP 405 (immutable)

Validates: Requirements 10.1, 10.2, 10.5, 10.6
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./_api_test_unused.db")

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


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
from backend.models.evidence_item import EvidenceItem
from backend.models.integrity_case import IntegrityCase
from backend.models.integrity_rule import IntegrityRule
from backend.models.learner import Learner
from backend.models.reviewer import Reviewer
from backend.models.similarity_report import SimilarityReport
from backend.models.submission import Submission


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session():
    """Function-scoped in-memory SQLite session with evidence-test seed data."""
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
            EvidenceItem.__table__,
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
            effective_from=datetime(2026, 1, 1).date(),
            is_active=True,
        )
    )

    # ── Submissions + similarity reports ─────────────────────────────────
    for i in range(1, 4):
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
    # INT-001: OPEN (active — evidence should be material)
    # INT-002: CLOSED (evidence added to it should be non-material)
    session.add(
        IntegrityCase(
            case_id="INT-2026-000001",
            report_id="SIM-SUB-2026-000001-01",
            case_status="OPEN",
            priority="HIGH",
            opened_at=datetime(2026, 2, 17),
            closed_at=None,
        )
    )
    session.add(
        IntegrityCase(
            case_id="INT-2026-000002",
            report_id="SIM-SUB-2026-000002-01",
            case_status="CLOSED",
            priority="MEDIUM",
            opened_at=datetime(2026, 2, 17),
            closed_at=datetime(2026, 3, 1),
        )
    )
    session.add(
        IntegrityCase(
            case_id="INT-2026-000003",
            report_id="SIM-SUB-2026-000003-01",
            case_status="OPEN",
            priority="LOW",
            opened_at=datetime(2026, 2, 18),
            closed_at=None,
        )
    )

    # ── Pre-existing evidence on INT-003 for ordering tests ──────────────
    session.add(
        EvidenceItem(
            evidence_id="EVD-000001",
            case_id="INT-2026-000003",
            evidence_type="DOCUMENT",
            description="First piece of evidence",
            added_by_role="INSTRUCTOR",
            added_at=datetime(2026, 2, 18, 10, 0, 0),
            is_material=True,
        )
    )
    session.add(
        EvidenceItem(
            evidence_id="EVD-000002",
            case_id="INT-2026-000003",
            evidence_type="QUOTATION",
            description="Second piece of evidence",
            added_by_role="REVIEWER",
            added_at=datetime(2026, 2, 18, 11, 0, 0),
            is_material=True,
        )
    )

    session.commit()

    yield session

    session.close()
    engine.dispose()


@pytest.fixture()
def client(db_session: Session):
    """FastAPI TestClient backed by the evidence test session."""
    app = create_app()

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /cases/{case_id}/evidence
# ---------------------------------------------------------------------------


VALID_PAYLOAD = {
    "evidence_type": "DOCUMENT",
    "description": "Submitted assignment PDF",
    "evidence_reference": "s3://bucket/file.pdf",
    "added_by_role": "INSTRUCTOR",
    "added_by_ref": "REV-001",
    "actor_role": "INSTRUCTOR",
}


class TestCreateEvidence:
    """Tests for POST /cases/{case_id}/evidence — Requirements 10.1, 10.2."""

    def test_returns_201_on_success(self, client):
        """Creating evidence returns HTTP 201."""
        resp = client.post("/cases/INT-2026-000001/evidence", json=VALID_PAYLOAD)
        assert resp.status_code == 201

    def test_response_body_shape(self, client):
        """Response body includes all EvidenceItemOut fields."""
        resp = client.post("/cases/INT-2026-000001/evidence", json=VALID_PAYLOAD)
        assert resp.status_code == 201
        body = resp.json()
        assert "evidence_id" in body
        assert "case_id" in body
        assert "evidence_type" in body
        assert "description" in body
        assert "added_at" in body
        assert "is_material" in body

    def test_response_links_correct_case(self, client):
        """The created evidence item belongs to the requested case."""
        resp = client.post("/cases/INT-2026-000001/evidence", json=VALID_PAYLOAD)
        assert resp.status_code == 201
        assert resp.json()["case_id"] == "INT-2026-000001"

    def test_evidence_id_generated(self, client):
        """evidence_id is auto-generated with the EVD- prefix."""
        resp = client.post("/cases/INT-2026-000001/evidence", json=VALID_PAYLOAD)
        assert resp.status_code == 201
        assert resp.json()["evidence_id"].startswith("EVD-")

    def test_is_material_true_for_open_case(self, client):
        """Evidence added to an OPEN case has is_material=True (Req 10.4)."""
        resp = client.post("/cases/INT-2026-000001/evidence", json=VALID_PAYLOAD)
        assert resp.status_code == 201
        assert resp.json()["is_material"] is True

    def test_is_material_false_for_closed_case(self, client):
        """Evidence added to a CLOSED case has is_material=False (Req 10.4)."""
        resp = client.post("/cases/INT-2026-000002/evidence", json=VALID_PAYLOAD)
        assert resp.status_code == 201
        assert resp.json()["is_material"] is False

    def test_404_for_unknown_case(self, client):
        """Unknown case_id returns HTTP 404."""
        resp = client.post("/cases/INT-NONEXISTENT/evidence", json=VALID_PAYLOAD)
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]

    def test_missing_required_field_422(self, client):
        """Missing evidence_type returns HTTP 422."""
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "evidence_type"}
        resp = client.post("/cases/INT-2026-000001/evidence", json=payload)
        assert resp.status_code == 422

    def test_evidence_persisted_in_db(self, client, db_session):
        """The evidence item is persisted to the database after POST."""
        resp = client.post("/cases/INT-2026-000001/evidence", json=VALID_PAYLOAD)
        assert resp.status_code == 201
        evidence_id = resp.json()["evidence_id"]

        db_session.expire_all()
        item = db_session.get(EvidenceItem, evidence_id)
        assert item is not None
        assert item.case_id == "INT-2026-000001"
        assert item.evidence_type == "DOCUMENT"


# ---------------------------------------------------------------------------
# GET /cases/{case_id}/evidence
# ---------------------------------------------------------------------------


class TestListEvidence:
    """Tests for GET /cases/{case_id}/evidence — Requirements 10.2, 10.6."""

    def test_returns_200_and_list(self, client):
        """Returns HTTP 200 with a JSON list."""
        resp = client.get("/cases/INT-2026-000003/evidence")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_returns_existing_evidence(self, client):
        """Returns the pre-seeded evidence items for the case."""
        resp = client.get("/cases/INT-2026-000003/evidence")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2

    def test_ordered_by_added_at_ascending(self, client):
        """Items are returned in ascending added_at order (Req 10.2)."""
        resp = client.get("/cases/INT-2026-000003/evidence")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2
        assert items[0]["evidence_id"] == "EVD-000001"
        assert items[1]["evidence_id"] == "EVD-000002"

    def test_empty_list_for_case_with_no_evidence(self, client):
        """Returns an empty list for a case with no evidence items."""
        resp = client.get("/cases/INT-2026-000001/evidence")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_404_for_unknown_case(self, client):
        """Unknown case_id returns HTTP 404 (Req 10.6)."""
        resp = client.get("/cases/INT-NONEXISTENT/evidence")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]

    def test_response_item_fields(self, client):
        """Each item in the list contains the required EvidenceItemOut fields."""
        resp = client.get("/cases/INT-2026-000003/evidence")
        assert resp.status_code == 200
        item = resp.json()[0]
        required_fields = {
            "evidence_id", "case_id", "evidence_type",
            "description", "added_at", "is_material",
            "added_by_role",
        }
        assert required_fields.issubset(item.keys())

    def test_new_evidence_appears_in_list(self, client):
        """Evidence added via POST shows up in a subsequent GET."""
        client.post("/cases/INT-2026-000001/evidence", json=VALID_PAYLOAD)
        resp = client.get("/cases/INT-2026-000001/evidence")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["evidence_type"] == "DOCUMENT"


# ---------------------------------------------------------------------------
# DELETE /cases/{case_id}/evidence — HTTP 405 (Requirement 10.5)
# ---------------------------------------------------------------------------


class TestDeleteEvidenceForbidden:
    """Tests for DELETE /cases/{case_id}/evidence — Requirement 10.5."""

    def test_delete_returns_405(self, client):
        """DELETE on evidence endpoint returns HTTP 405."""
        resp = client.delete("/cases/INT-2026-000001/evidence")
        assert resp.status_code == 405

    def test_delete_405_detail_message(self, client):
        """405 response body contains expected detail text."""
        resp = client.delete("/cases/INT-2026-000001/evidence")
        body = resp.json()
        assert "detail" in body
        assert "immutable" in body["detail"].lower()


# ---------------------------------------------------------------------------
# PUT /cases/{case_id}/evidence — HTTP 405 (Requirement 10.5)
# ---------------------------------------------------------------------------


class TestPutEvidenceForbidden:
    """Tests for PUT /cases/{case_id}/evidence — Requirement 10.5."""

    def test_put_returns_405(self, client):
        """PUT on evidence endpoint returns HTTP 405."""
        resp = client.put("/cases/INT-2026-000001/evidence", json={})
        assert resp.status_code == 405

    def test_put_405_detail_message(self, client):
        """405 response body contains expected detail text."""
        resp = client.put("/cases/INT-2026-000001/evidence", json={})
        body = resp.json()
        assert "detail" in body
        assert "immutable" in body["detail"].lower()
