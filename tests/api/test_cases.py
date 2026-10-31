"""
tests/api/test_cases.py

API-level integration tests for the Cases router
(backend/routers/cases.py).

Covers:
    GET /cases                         — list with filters and pagination
    GET /cases/{case_id}               — detail; 404 if not found
    PATCH /cases/{case_id}/status      — status update; 404, 422

Validates: Requirements 8.1, 8.2, 8.3, 8.5, 8.6, 8.7
"""

from datetime import datetime

import pytest

from backend.models.case_event import CaseEvent


# ── GET /cases — list endpoint ──────────────────────────────────────────────


class TestListCases:
    """Tests for GET /cases — Requirements 8.1, 8.7."""

    def test_returns_all_cases_by_default(self, client):
        resp = client.get("/cases")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_count"] == 3
        assert len(body["items"]) == 3
        assert body["page"] == 1
        assert body["page_size"] == 20

    def test_pagination_envelope(self, client):
        """Response has total_count, page, page_size; len(items) <= page_size."""
        resp = client.get("/cases?page=1&page_size=2")
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) == {"items", "total_count", "page", "page_size"}
        assert body["total_count"] == 3
        assert len(body["items"]) <= body["page_size"]
        assert body["page"] == 1
        assert body["page_size"] == 2

    def test_pagination_second_page(self, client):
        """Page 2 with page_size=2 returns the remaining 1 item."""
        resp = client.get("/cases?page=2&page_size=2")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_count"] == 3
        assert len(body["items"]) == 1
        assert body["page"] == 2

    def test_filter_by_status(self, client):
        """Filtering by status=OPEN returns only OPEN cases."""
        resp = client.get("/cases?status=OPEN")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_count"] == 1
        assert body["items"][0]["case_id"] == "INT-2026-000001"
        assert body["items"][0]["case_status"] == "OPEN"

    def test_filter_by_priority(self, client):
        """Filtering by priority=HIGH returns only HIGH priority cases."""
        resp = client.get("/cases?priority=HIGH")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_count"] == 1
        assert body["items"][0]["case_id"] == "INT-2026-000001"
        assert body["items"][0]["priority"] == "HIGH"

    def test_filter_by_assigned_reviewer_id(self, client):
        """Filtering by assigned_reviewer_id returns cases with that reviewer."""
        resp = client.get("/cases?assigned_reviewer_id=REV-002")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_count"] == 2
        ids = {item["case_id"] for item in body["items"]}
        assert ids == {"INT-2026-000002", "INT-2026-000003"}

    def test_filter_by_assigned_reviewer_no_match(self, client):
        """Filtering by a non-existent reviewer returns 0 cases."""
        resp = client.get("/cases?assigned_reviewer_id=REV-999")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_count"] == 0
        assert len(body["items"]) == 0

    def test_combined_filter_status_and_priority(self, client):
        """Combining status and priority filters."""
        resp = client.get("/cases?status=UNDER_REVIEW&priority=MEDIUM")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_count"] == 1
        assert body["items"][0]["case_id"] == "INT-2026-000002"

    def test_has_conflict_field(self, client):
        """has_conflict is computed from reviewer conflict_status."""
        resp = client.get("/cases?status=UNDER_REVIEW")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"][0]["has_conflict"] is True

    def test_page_too_low_rejected(self, client):
        """page < 1 is rejected by validation."""
        resp = client.get("/cases?page=0")
        assert resp.status_code == 422

    def test_page_size_too_large_rejected(self, client):
        """page_size > 100 is rejected by validation."""
        resp = client.get("/cases?page_size=101")
        assert resp.status_code == 422


# ── GET /cases/{case_id} — detail endpoint ──────────────────────────────────


class TestGetCase:
    """Tests for GET /cases/{case_id} — Requirements 8.2, 8.5."""

    def test_returns_case_detail(self, client):
        """Detail includes the case_id and report summary."""
        resp = client.get("/cases/INT-2026-000001")
        assert resp.status_code == 200
        body = resp.json()
        assert body["case_id"] == "INT-2026-000001"
        assert body["case_status"] == "OPEN"
        assert body["report_summary"]["report_id"] == "SIM-SUB-2026-000001-01"
        assert body["report_summary"]["similarity_score"] == 85.50

    def test_detail_includes_reviewers(self, client):
        """Detail includes the list of assigned reviewers."""
        resp = client.get("/cases/INT-2026-000002")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["reviewers"]) == 2
        reviewer_ids = {r["reviewer_id"] for r in body["reviewers"]}
        assert reviewer_ids == {"REV-001", "REV-002"}

    def test_detail_includes_decision(self, client):
        """Detail includes the final decision summary when present."""
        resp = client.get("/cases/INT-2026-000003")
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision_summary"] is not None
        assert body["decision_summary"]["decision_outcome"] == "VIOLATION"
        assert body["decision_summary"]["is_final"] is True

    def test_detail_no_decision(self, client):
        """Detail has decision_summary=None when no decision exists."""
        resp = client.get("/cases/INT-2026-000001")
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision_summary"] is None

    def test_detail_includes_events(self, client):
        """Detail includes the case event timeline."""
        resp = client.get("/cases/INT-2026-000003")
        assert resp.status_code == 200
        body = resp.json()
        event_types = {e["event_type"] for e in body["events"]}
        assert "CASE_CREATED" in event_types
        assert "DECISION_RECORDED" in event_types

    def test_404_for_unknown_case(self, client):
        """Unknown case_id returns HTTP 404 with structured detail body."""
        resp = client.get("/cases/INT-2026-999999")
        assert resp.status_code == 404
        body = resp.json()
        assert "detail" in body
        assert "not found" in body["detail"]


# ── PATCH /cases/{case_id}/status — status update ────────────────────────────


class TestPatchCaseStatus:
    """Tests for PATCH /cases/{case_id}/status — Requirements 8.3, 8.5, 8.6."""

    def test_valid_transition(self, client, db_session):
        """OPEN -> UNDER_REVIEW is valid and returns updated case."""
        resp = client.patch(
            "/cases/INT-2026-000001/status",
            json={
                "case_status": "UNDER_REVIEW",
                "actor_role": "REVIEWER",
                "actor_ref": "REV-001",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["case_id"] == "INT-2026-000001"
        assert body["case_status"] == "UNDER_REVIEW"
        db_session.commit()

    def test_invalid_transition_422(self, client):
        """DECIDED -> OPEN is an invalid transition -> HTTP 422."""
        # INT-003 is DECIDED; OPEN is not a valid target from DECIDED
        resp = client.patch(
            "/cases/INT-2026-000003/status",
            json={"case_status": "OPEN", "actor_role": "SYSTEM"},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert "Invalid status transition" in body["detail"]

    def test_404_for_unknown_case(self, client):
        """Unknown case_id returns HTTP 404."""
        resp = client.patch(
            "/cases/INT-2026-999999/status",
            json={"case_status": "UNDER_REVIEW", "actor_role": "SYSTEM"},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]

    def test_inserts_status_changed_event(self, client, db_session):
        """Every successful status update inserts a STATUS_CHANGED CaseEvent
        (Requirement 8.4).
        """
        before = (
            db_session.query(CaseEvent)
            .filter(
                CaseEvent.case_id == "INT-2026-000002",
                CaseEvent.event_type == "STATUS_CHANGED",
            )
            .count()
        )
        assert before == 0

        resp = client.patch(
            "/cases/INT-2026-000002/status",
            json={
                "case_status": "AWAITING_INFORMATION",
                "actor_role": "REVIEWER",
            },
        )
        assert resp.status_code == 200
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

    def test_missing_required_field_422(self, client):
        """Missing actor_role in request body -> HTTP 422."""
        resp = client.patch(
            "/cases/INT-2026-000001/status",
            json={"case_status": "UNDER_REVIEW"},
        )
        assert resp.status_code == 422

    def test_invalid_status_value_422(self, client):
        """Invalid case_status value -> HTTP 422."""
        resp = client.patch(
            "/cases/INT-2026-000001/status",
            json={"case_status": "INVALID", "actor_role": "SYSTEM"},
        )
        assert resp.status_code == 422
