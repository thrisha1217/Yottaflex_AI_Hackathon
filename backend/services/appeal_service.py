"""
backend/services/appeal_service.py

Service layer for appeal and appeal review endpoints (Requirement 12).

All functions receive the caller's SQLAlchemy ``Session`` and perform
mutations that write rows via ``db.add()`` **without committing**. The
transaction boundary is owned by the router layer — services never call
``db.commit()`` or ``db.rollback()``. This keeps Appeal, AppealReview,
CaseEvent, and AuditLog writes in the same transaction so a failed rollback
cleans up the data and its audit trail together.

Requirements validated: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 21.1
"""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.appeal import Appeal
from backend.models.appeal_review import AppealReview
from backend.models.case_reviewer import CaseReviewer
from backend.models.integrity_case import IntegrityCase
from backend.schemas.appeals import AppealCreate, AppealOut, AppealReviewCreate, AppealReviewOut
from backend.services import audit_service

# Outcomes that constitute a resolved appeal and require independence_verified = TRUE
_RESOLVED_OUTCOMES = {"UPHELD", "OVERTURNED"}


def create_appeal(
    db: Session,
    case_id: str,
    payload: AppealCreate,
    actor=None,
) -> AppealOut:
    """Create an Appeal record for an IntegrityCase (Requirement 12.1).

    Guards:
        - Case must exist (404 if not found).

    On success:
        - Generates ``appeal_id`` as ``APL-{count+1:06d}``.
        - Sets ``appeal_no`` as the count of existing appeals on this case + 1.
        - Inserts an ``Appeal`` row with ``appeal_status="SUBMITTED"`` and
          ``submitted_at=now()``.
        - Updates ``case.case_status`` to ``"APPEAL_PENDING"``
          (Requirement 12.7).
        - Inserts an ``APPEAL_SUBMITTED`` CaseEvent (Requirement 12.7).
        - Writes an AuditLog for the Appeal INSERT (Requirement 13.4).
        - Writes an AuditLog for the IntegrityCase UPDATE (Requirement 13.4).
        - Does **not** commit — the caller owns the transaction boundary.

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        case_id: The primary key of the IntegrityCase.
        payload: ``AppealCreate`` containing ``learner_id``, ``reason``,
            and ``actor_role``.
        actor: Optional actor override (unused; actor info comes from
            ``payload``).

    Returns:
        ``AppealOut`` reflecting the newly created Appeal.
    """
    # ── Verify the case exists (404) ──────────────────────────────────────
    case = db.execute(
        select(IntegrityCase).where(IntegrityCase.case_id == case_id)
    ).scalars().first()
    if case is None:
        raise HTTPException(
            status_code=404, detail=f"IntegrityCase {case_id} not found"
        )

    # ── Generate appeal_id: APL-{count+1:06d} ────────────────────────────
    total_count = db.execute(
        select(func.count()).select_from(Appeal)
    ).scalar_one()
    appeal_id = f"APL-{total_count + 1:06d}"

    # ── Determine appeal_no for this case ─────────────────────────────────
    case_appeal_count = db.execute(
        select(func.count()).select_from(Appeal).where(Appeal.case_id == case_id)
    ).scalar_one()
    appeal_no = case_appeal_count + 1

    # ── Insert Appeal record (Requirement 12.1) ───────────────────────────
    now = datetime.utcnow()
    appeal = Appeal(
        appeal_id=appeal_id,
        case_id=case_id,
        learner_id=payload.learner_id,
        appeal_no=appeal_no,
        reason=payload.reason,
        submitted_at=now,
        appeal_status="SUBMITTED",
        resolved_at=None,
    )
    db.add(appeal)
    db.flush()

    # ── Capture old case_status before mutation ───────────────────────────
    old_case_status = case.case_status

    # ── Update case_status to APPEAL_PENDING (Requirement 12.7) ──────────
    case.case_status = "APPEAL_PENDING"

    # ── Build audit value snapshots ───────────────────────────────────────
    appeal_new_values = {
        "appeal_id": appeal_id,
        "case_id": case_id,
        "learner_id": payload.learner_id,
        "appeal_no": appeal_no,
        "reason": payload.reason,
        "submitted_at": now.isoformat(),
        "appeal_status": "SUBMITTED",
        "resolved_at": None,
    }

    case_old_values = {"case_status": old_case_status}
    case_new_values = {"case_status": "APPEAL_PENDING"}

    # ── Insert APPEAL_SUBMITTED CaseEvent (Requirement 12.7) ─────────────
    audit_service.insert_case_event(
        db=db,
        case_id=case_id,
        event_type="APPEAL_SUBMITTED",
        actor_role=payload.actor_role,
        prev_status=old_case_status,
        new_status="APPEAL_PENDING",
        details={"appeal_id": appeal_id},
        actor_ref=payload.learner_id,
    )

    # ── Write AuditLog for Appeal INSERT (Requirement 13.4) ───────────────
    audit_service.log_insert(
        db=db,
        entity_type="Appeal",
        entity_id=appeal_id,
        new_values=appeal_new_values,
        actor_role=payload.actor_role,
        actor_ref=payload.learner_id,
    )

    # ── Write AuditLog for IntegrityCase UPDATE (Requirement 13.4) ────────
    audit_service.log_update(
        db=db,
        entity_type="IntegrityCase",
        entity_id=case_id,
        old_values=case_old_values,
        new_values=case_new_values,
        actor_role=payload.actor_role,
        actor_ref=payload.learner_id,
    )

    return AppealOut.model_validate(appeal)


def create_appeal_review(
    db: Session,
    appeal_id: str,
    payload: AppealReviewCreate,
    actor=None,
) -> AppealReviewOut:
    """Create an AppealReview record for an Appeal (Requirement 12.3).

    Guards (design guard pattern):
        - Appeal must exist (404 if not found).
        - ``reviewer_id`` must differ from the PRIMARY CaseReviewer of the
          linked IntegrityCase (HTTP 409 if same) (Requirement 12.4).
        - If ``outcome`` is ``UPHELD`` or ``OVERTURNED``, then
          ``independence_verified`` must be ``True``; otherwise HTTP 422
          (Requirement 12.6 / 21.1).

    On success:
        - Inserts an ``AppealReview`` row with ``reviewed_at=now()``.
        - If ``outcome`` in ``{UPHELD, OVERTURNED}`` and
          ``independence_verified=True``: updates ``Appeal.appeal_status``
          to the outcome value and sets ``Appeal.resolved_at = now()``
          (Requirement 12.5).
        - Writes an AuditLog for the AppealReview INSERT (Requirement 13.4).
        - If Appeal was updated: writes an AuditLog for the Appeal UPDATE
          (Requirement 13.4).
        - Does **not** commit — the caller owns the transaction boundary.

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        appeal_id: The primary key of the Appeal.
        payload: ``AppealReviewCreate`` containing ``reviewer_id``,
            ``outcome``, ``rationale``, ``independence_verified``, and
            ``actor_role``.
        actor: Optional actor override (unused; actor info comes from
            ``payload``).

    Returns:
        ``AppealReviewOut`` reflecting the newly created AppealReview.
    """
    # ── Fetch the Appeal (404 if not found) ───────────────────────────────
    appeal = db.execute(
        select(Appeal).where(Appeal.appeal_id == appeal_id)
    ).scalars().first()
    if appeal is None:
        raise HTTPException(
            status_code=404, detail=f"Appeal {appeal_id} not found"
        )

    # ── Guard: reviewer must differ from PRIMARY CaseReviewer (409) ───────
    # Find the PRIMARY reviewer on the linked IntegrityCase.
    primary_reviewer = db.execute(
        select(CaseReviewer).where(
            CaseReviewer.case_id == appeal.case_id,
            CaseReviewer.assignment_role == "PRIMARY",
            CaseReviewer.unassigned_at.is_(None),  # active assignment only
        )
    ).scalars().first()

    if primary_reviewer is not None and primary_reviewer.reviewer_id == payload.reviewer_id:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Reviewer {payload.reviewer_id} is the PRIMARY CaseReviewer "
                f"for case {appeal.case_id} and cannot conduct the appeal review."
            ),
        )

    # ── Guard: UPHELD/OVERTURNED requires independence_verified=True (422) ─
    # (Requirement 12.6 / 21.1)
    if payload.outcome in _RESOLVED_OUTCOMES and not payload.independence_verified:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Outcome '{payload.outcome}' requires independence_verified = TRUE. "
                "Set independence_verified to true to record this outcome."
            ),
        )

    # ── Insert AppealReview record (Requirement 12.3) ─────────────────────
    now = datetime.utcnow()
    review = AppealReview(
        appeal_id=appeal_id,
        reviewer_id=payload.reviewer_id,
        outcome=payload.outcome,
        rationale=payload.rationale,
        independence_verified=payload.independence_verified,
        reviewed_at=now,
    )
    db.add(review)
    db.flush()

    review_new_values = {
        "review_id": review.review_id,
        "appeal_id": appeal_id,
        "reviewer_id": payload.reviewer_id,
        "outcome": payload.outcome,
        "rationale": payload.rationale,
        "independence_verified": payload.independence_verified,
        "reviewed_at": now.isoformat(),
    }

    # ── Write AuditLog for AppealReview INSERT (Requirement 13.4) ─────────
    audit_service.log_insert(
        db=db,
        entity_type="AppealReview",
        entity_id=str(review.review_id),
        new_values=review_new_values,
        actor_role=payload.actor_role,
        actor_ref=payload.reviewer_id,
    )

    # ── Resolve the Appeal if outcome is UPHELD/OVERTURNED (Requirement 12.5) ──
    if payload.outcome in _RESOLVED_OUTCOMES and payload.independence_verified:
        old_appeal_status = appeal.appeal_status
        old_resolved_at = appeal.resolved_at

        appeal.appeal_status = payload.outcome
        appeal.resolved_at = now

        appeal_old_values = {
            "appeal_status": old_appeal_status,
            "resolved_at": old_resolved_at.isoformat() if old_resolved_at else None,
        }
        appeal_new_values = {
            "appeal_status": payload.outcome,
            "resolved_at": now.isoformat(),
        }

        audit_service.log_update(
            db=db,
            entity_type="Appeal",
            entity_id=appeal_id,
            old_values=appeal_old_values,
            new_values=appeal_new_values,
            actor_role=payload.actor_role,
            actor_ref=payload.reviewer_id,
        )

    return AppealReviewOut.model_validate(review)


def get_appeals(db: Session, case_id: str) -> list[AppealOut]:
    """Return all Appeal records for an IntegrityCase ordered by
    ``submitted_at`` ascending (Requirement 12.2).

    Raises ``HTTPException`` with status 404 if the case is not found.

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        case_id: The primary key of the IntegrityCase.

    Returns:
        List of ``AppealOut`` ordered by ``submitted_at`` ascending.
    """
    # ── Verify the case exists (404) ──────────────────────────────────────
    case = db.execute(
        select(IntegrityCase).where(IntegrityCase.case_id == case_id)
    ).scalars().first()
    if case is None:
        raise HTTPException(
            status_code=404, detail=f"IntegrityCase {case_id} not found"
        )

    # ── Query appeals ordered by submitted_at ascending ───────────────────
    stmt = (
        select(Appeal)
        .where(Appeal.case_id == case_id)
        .order_by(Appeal.submitted_at.asc())
    )
    appeals = db.execute(stmt).scalars().all()

    return [AppealOut.model_validate(a) for a in appeals]
