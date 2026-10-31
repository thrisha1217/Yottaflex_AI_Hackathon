"""
backend/services/audit_reports_service.py

Service layer for the Audit and Compliance Reporting endpoints (Requirement 20).

Functions
---------
conflict_reassignments              – Req 20.1
post_decision_evidence              – Req 20.2
appeals_without_independent_review  – Req 20.3
case_event_log                      – Req 20.6
"""

from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models.appeal import Appeal
from backend.models.appeal_review import AppealReview
from backend.models.case_event import CaseEvent
from backend.models.case_reviewer import CaseReviewer
from backend.models.evidence_item import EvidenceItem
from backend.models.integrity_case import IntegrityCase
from backend.models.reviewer import Reviewer
from backend.schemas.audit_reports import (
    AppealsWithoutReviewOut,
    ConflictReassignmentOut,
    EvidenceItemSummary,
    PostDecisionEvidenceOut,
)
from backend.schemas.cases import CaseEventOut


# ---------------------------------------------------------------------------
# 20.1  Conflict reassignments
# ---------------------------------------------------------------------------


def conflict_reassignments(db: Session) -> list[ConflictReassignmentOut]:
    """Return all CaseReviewer rows with conflict_status = CONFLICT.

    Joins to Reviewer to resolve reviewer_name.

    Validates: Requirements 20.1
    """
    rows = (
        db.query(CaseReviewer, Reviewer.full_name)
        .join(Reviewer, CaseReviewer.reviewer_id == Reviewer.reviewer_id)
        .filter(CaseReviewer.conflict_status == "CONFLICT")
        .order_by(CaseReviewer.assigned_at.desc())
        .all()
    )

    return [
        ConflictReassignmentOut(
            assignment_id=cr.assignment_id,
            case_id=cr.case_id,
            reviewer_id=cr.reviewer_id,
            reviewer_name=full_name or cr.reviewer_id,
            conflict_reason=cr.conflict_reason,
            assigned_at=cr.assigned_at,
            unassigned_at=cr.unassigned_at,
        )
        for cr, full_name in rows
    ]


# ---------------------------------------------------------------------------
# 20.2  Post-decision evidence
# ---------------------------------------------------------------------------


def post_decision_evidence(db: Session) -> list[PostDecisionEvidenceOut]:
    """Return EvidenceItem rows where is_material = FALSE, grouped by case_id.

    These are items added after a Decision was recorded (the service layer
    sets is_material=FALSE when a case is CLOSED at the time of submission).

    Validates: Requirements 20.2
    """
    items = (
        db.query(EvidenceItem)
        .filter(EvidenceItem.is_material.is_(False))
        .order_by(EvidenceItem.case_id, EvidenceItem.added_at)
        .all()
    )

    grouped: dict[str, list[EvidenceItemSummary]] = defaultdict(list)
    for item in items:
        grouped[item.case_id].append(
            EvidenceItemSummary(
                evidence_id=item.evidence_id,
                evidence_type=item.evidence_type,
                description=item.description,
                added_at=item.added_at,
                is_material=item.is_material,
            )
        )

    return [
        PostDecisionEvidenceOut(case_id=case_id, evidence=evidence_list)
        for case_id, evidence_list in grouped.items()
    ]


# ---------------------------------------------------------------------------
# 20.3  Appeals without independent review
# ---------------------------------------------------------------------------


def appeals_without_independent_review(db: Session) -> list[AppealsWithoutReviewOut]:
    """Return Appeal rows with appeal_status UPHELD or OVERTURNED that have
    no AppealReview with independence_verified = TRUE.

    By design this should always be empty (the API guards against it).
    This endpoint surfaces any data integrity violations.

    Validates: Requirements 20.3
    """
    # Subquery: appeal_ids that DO have an independent review
    independent_review_subq = (
        db.query(AppealReview.appeal_id)
        .filter(AppealReview.independence_verified.is_(True))
        .subquery()
    )

    appeals = (
        db.query(Appeal)
        .filter(Appeal.appeal_status.in_(["UPHELD", "OVERTURNED"]))
        .filter(
            Appeal.appeal_id.not_in(
                db.query(independent_review_subq.c.appeal_id)
            )
        )
        .order_by(Appeal.submitted_at.desc())
        .all()
    )

    return [
        AppealsWithoutReviewOut(
            appeal_id=a.appeal_id,
            case_id=a.case_id,
            appeal_status=a.appeal_status,
            submitted_at=a.submitted_at,
        )
        for a in appeals
    ]


# ---------------------------------------------------------------------------
# 20.6  Case event log
# ---------------------------------------------------------------------------


def case_event_log(db: Session, case_id: str) -> list[CaseEventOut]:
    """Return the full CaseEvent timeline for one case in ascending
    occurred_at order.

    Raises HTTP 404 if the case does not exist.

    Validates: Requirements 20.6
    """
    case = db.get(IntegrityCase, case_id)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail=f"IntegrityCase {case_id!r} not found",
        )

    events = (
        db.query(CaseEvent)
        .filter(CaseEvent.case_id == case_id)
        .order_by(CaseEvent.occurred_at.asc())
        .all()
    )

    return [CaseEventOut.model_validate(e) for e in events]
