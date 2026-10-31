"""
tests/api/test_reviewers.py

API-level integration tests for the Reviewers router
(backend/routers/reviewers.py).

Covers:
    GET /reviewers                                         — paginated list of
      active reviewers (Requirement 9.6).
    POST /cases/{case_id}/reviewers                        — assign reviewer;
      404, 409, 422 (Requirements 9.1, 9.5, 21.3).
    PATCH /cases/{case_id}/reviewers/{assignment_id}/conflict — declare conflict;
      404, 422 (Requirements 9.2, 9.3, 9.4, 21.4).

Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 21.3, 21.4
"""

from datetime import datetime

import pytest

from backend.models.case_event import CaseEvent
from backend.models.case_reviewer import CaseReviewer
from backend.models.integrity_case import IntegrityCase


# ── GET /reviewers — list endpoint ──────────────────────────────────────────


class TestListReviewers:
    """Tests for GET /reviewers — Requirement 9.6."""

    def test_returns_active_reviewers_only(self, client):
        """Only ACTIVE reviewers are returned; INACTIVE ones excluded."""
        resp = client.get("/reviewers")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_count"] == 2  # REV-001, REV-002; REV-003 is INACTIVE
        assert len(body["items"]) == 2
        ids = {r["reviewer_id"] for r in body["items"]}
        assert ids == {"REV-001", "REV-002"}
        for r in body["items"]:
            assert r["status"] == "ACTIVE"

    def test_pagination_envelope(self, client):
        """Response has total_count, page, page_size; len(items) <= page_size."""
        resp = client.get("/reviewers?page=1&page_size=1")
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) == {"items", "total_count", "page", "page_size"}
        assert body["total_count"] == 2
        assert len(body["items"]) <= body["page_size"]
        assert body["page"] == 1
        assert body["page_size"] == 1

    def test_pagination_second_page(self, client):
        """Page 2 with page_size=1 returns the remaining 1 item."""
        resp = client.get("/reviewers?page=2&page_size=1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_count"] == 2
        assert len(body["items"]) == 1
        assert body["page"] == 2

    def test_reviewer_out_fields(self, client):
        """Each item has the expected ReviewerOut fields."""
        resp = client.get("/reviewers")
        assert resp.status_code == 200
        reviewer = resp.json()["items"][0]
        for field in ("reviewer_id", "full_name", "email", "reviewer_role", "status", "created_at"):
            assert field in reviewer

    def test_page_too_low_rejected(self, client):
        """page < 1 is rejected by validation."""
        resp = client.get("/reviewers?page=0")
        assert resp.status_code == 422

    def test_page_size_too_large_rejected(self, client):
        """page_size > 100 is rejected by validation."""
        resp = client.get("/reviewers?page_size=101")
        assert resp.status_code == 422


# ── POST /cases/{case_id}/reviewers — assign reviewer ───────────────────────


class TestAssignReviewer:
    """Tests for POST /cases/{case_id}/reviewers — Requirements 9.1, 9.5, 21.3."""

    def test_assigns_active_reviewer(self, client):
        """Assigning an ACTIVE reviewer returns 201 with the assignment."""
        resp = client.post(
            "/cases/INT-2026-000001/reviewers",
            json={
                "reviewer_id": "REV-002",
                "assignment_role": "SECONDARY",
                "actor_role": "ACADEMIC_ADMIN",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["case_id"] == "INT-2026-000001"
        assert body["reviewer_id"] == "REV-002"
        assert body["assignment_role"] == "SECONDARY"
        assert body["conflict_status"] == "PENDING"
        assert body["unassigned_at"] is None

    def test_404_for_unknown_case(self, client):
        """Unknown case_id returns HTTP 404."""
        resp = client.post(
            "/cases/INT-2026-999999/reviewers",
            json={
                "reviewer_id": "REV-001",
                "assignment_role": "PRIMARY",
                "actor_role": "SYSTEM",
            },
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]

    def test_404_for_unknown_reviewer(self, client):
        """Unknown reviewer_id returns HTTP 404."""
        resp = client.post(
            "/cases/INT-2026-000001/reviewers",
            json={
                "reviewer_id": "REV-999",
                "assignment_role": "PRIMARY",
                "actor_role": "SYSTEM",
            },
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]

    def test_422_for_inactive_reviewer(self, client):
        """Property 27: Inactive reviewer rejected — POST with INACTIVE
        reviewer returns HTTP 422 (Requirement 21.3).

        REV-003 has status=INACTIVE.
        """
        resp = client.post(
            "/cases/INT-2026-000001/reviewers",
            json={
                "reviewer_id": "REV-003",
                "assignment_role": "PRIMARY",
                "actor_role": "SYSTEM",
            },
        )
        assert resp.status_code == 422
        assert "not active" in resp.json()["detail"]

    def test_409_for_active_conflict(self, client):
        """Assigning a reviewer who already has a CONFLICT on the same case
        returns HTTP 409 (Requirement 9.5).

        REV-002 already has a CONFLICT assignment on INT-2026-000002.
        """
        resp = client.post(
            "/cases/INT-2026-000002/reviewers",
            json={
                "reviewer_id": "REV-002",
                "assignment_role": "PRIMARY",
                "actor_role": "ACADEMIC_ADMIN",
            },
        )
        assert resp.status_code == 409
        assert "conflict" in resp.json()["detail"].lower()

    def test_inserts_reviewer_assigned_case_event(self, client, db_session):
        """Every successful POST inserts a REVIEWER_ASSIGNED CaseEvent
        (Requirement 9.1 side-effect).
        """
        before = (
            db_session.query(CaseEvent)
            .filter(
                CaseEvent.case_id == "INT-2026-000001",
                CaseEvent.event_type == "REVIEWER_ASSIGNED",
            )
            .count()
        )
        # Conftest already has 1 REVIEWER_ASSIGNED for INT-001
        assert before == 1

        resp = client.post(
            "/cases/INT-2026-000001/reviewers",
            json={
                "reviewer_id": "REV-002",
                "assignment_role": "SECONDARY",
                "actor_role": "ACADEMIC_ADMIN",
            },
        )
        assert resp.status_code == 201

        after = (
            db_session.query(CaseEvent)
            .filter(
                CaseEvent.case_id == "INT-2026-000001",
                CaseEvent.event_type == "REVIEWER_ASSIGNED",
            )
            .count()
        )
        assert after == 2

    def test_missing_required_field_422(self, client):
        """Missing assignment_role in request body returns HTTP 422."""
        resp = client.post(
            "/cases/INT-2026-000001/reviewers",
            json={
                "reviewer_id": "REV-001",
                "actor_role": "SYSTEM",
            },
        )
        assert resp.status_code == 422


# ── PATCH /cases/{case_id}/reviewers/{assignment_id}/conflict ───────────────


class TestUpdateConflict:
    """Tests for PATCH .../conflict — Requirements 9.2, 9.3, 9.4, 21.4."""

    def test_sets_conflict_status_and_unassigned_at(self, client):
        """Property 22: Conflict declaration sets unassigned_at (Requirement 9.3).

        Assignment 1 (INT-001, REV-001, PRIMARY, PENDING).
        """
        resp = client.patch(
            "/cases/INT-2026-000001/reviewers/1/conflict",
            json={
                "conflict_status": "CONFLICT",
                "conflict_reason": "Personal relationship with learner",
                "actor_role": "ACADEMIC_ADMIN",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["conflict_status"] == "CONFLICT"
        assert body["unassigned_at"] is not None
        assert body["conflict_reason"] == "Personal relationship with learner"

    def test_inserts_reviewer_conflict_declared_case_event(self, client, db_session):
        """Property 22: Conflict declaration inserts REVIEWER_CONFLICT_DECLARED
        CaseEvent (Requirement 9.4).

        Assignment 2 (INT-002, REV-001, PRIMARY, PENDING).
        """
        before = (
            db_session.query(CaseEvent)
            .filter(
                CaseEvent.case_id == "INT-2026-000002",
                CaseEvent.event_type == "REVIEWER_CONFLICT_DECLARED",
            )
            .count()
        )
        assert before == 0

        resp = client.patch(
            "/cases/INT-2026-000002/reviewers/2/conflict",
            json={
                "conflict_status": "CONFLICT",
                "actor_role": "ACADEMIC_ADMIN",
            },
        )
        assert resp.status_code == 200

        after = (
            db_session.query(CaseEvent)
            .filter(
                CaseEvent.case_id == "INT-2026-000002",
                CaseEvent.event_type == "REVIEWER_CONFLICT_DECLARED",
            )
            .count()
        )
        assert after == 1

    def test_404_for_unknown_case(self, client):
        """Unknown case_id returns HTTP 404."""
        resp = client.patch(
            "/cases/INT-2026-999999/reviewers/1/conflict",
            json={
                "conflict_status": "CONFLICT",
                "actor_role": "SYSTEM",
            },
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]

    def test_404_for_unknown_assignment(self, client):
        """Unknown assignment_id returns HTTP 404."""
        resp = client.patch(
            "/cases/INT-2026-000001/reviewers/99999/conflict",
            json={
                "conflict_status": "CONFLICT",
                "actor_role": "SYSTEM",
            },
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]

    def test_404_for_assignment_wrong_case(self, client):
        """Assignment belonging to a different case returns HTTP 404.

        Assignment 2 belongs to INT-002, not INT-001.
        """
        resp = client.patch(
            "/cases/INT-2026-000001/reviewers/2/conflict",
            json={
                "conflict_status": "CONFLICT",
                "actor_role": "SYSTEM",
            },
        )
        assert resp.status_code == 404

    def test_422_for_closed_case(self, client, db_session):
        """Declaring a conflict on a CLOSED case returns HTTP 422
        (Requirement 21.4).

        The conftest has no CLOSED case, so we create one using the
        unused SIM-SUB-2026-000004-01 report.
        """
        db_session.add(
            IntegrityCase(
                case_id="INT-2026-CLOSED",
                report_id="SIM-SUB-2026-000004-01",
                case_status="CLOSED",
                priority="LOW",
                opened_at=datetime(2026, 3, 1),
                closed_at=datetime(2026, 3, 10),
            )
        )
        db_session.add(
            CaseReviewer(
                assignment_id=100,
                case_id="INT-2026-CLOSED",
                reviewer_id="REV-001",
                assignment_role="PRIMARY",
                assigned_at=datetime(2026, 3, 1, 12),
                conflict_status="PENDING",
            )
        )
        db_session.commit()

        resp = client.patch(
            "/cases/INT-2026-CLOSED/reviewers/100/conflict",
            json={
                "conflict_status": "CONFLICT",
                "actor_role": "ACADEMIC_ADMIN",
            },
        )
        assert resp.status_code == 422
        assert "CLOSED" in resp.json()["detail"]

    def test_missing_required_field_422(self, client):
        """Missing actor_role in request body returns HTTP 422."""
        resp = client.patch(
            "/cases/INT-2026-000001/reviewers/1/conflict",
            json={
                "conflict_status": "CONFLICT",
            },
        )
        assert resp.status_code == 422
