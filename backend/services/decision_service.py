"""
backend/services/decision_service.py

Service layer for decision endpoints (Requirement 11).

All functions receive the caller's SQLAlchemy ``Session`` and perform
mutations that write rows via ``db.add()`` **without committing**. The
transaction boundary is owned by the router layer — services never call
``db.commit()`` or ``db.rollback()``. This keeps Decision, DecisionEvidence,
CaseEvent, and AuditLog writes in the same transaction so a failed rollback
cleans up the data and its audit trail together.

Requirements validated: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 21.2
"""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.appeal import Appeal
from backend.models.decision import Decision
from backend.models.decision_evidence import DecisionEvidence
from backend.models.integrity_case import IntegrityCase
from backend.schemas.decisions import DecisionCreate, DecisionOut
from backend.services import audit_service


def create_decision(
    db: Session,
    case_id: str,
    payload: DecisionCreate,
    actor=None,
) -> DecisionOut:
    """Create a Decision record for an IntegrityCase (Requirement 11.1).

    Guards:
        - Case must exist (404 if not found).
        - Case must not already have a final Decision (``is_final=True``) with
          no pending appeal (``appeal_status=SUBMITTED`` or ``UNDER_REVIEW``);
          if it does, raise HTTP 409 (Requirement 21.2).
        - If ``previous_decision_id`` is provided, the referenced Decision must
          belong to the same ``case_id``; if not, raise HTTP 422
          (Requirement 11.4).

    On success:
        - Inserts a Decision row with ``is_final=True`` and
          ``decided_at=now()`` (Requirement 11.1).
        - Flushes to obtain the generated ``decision_id`` PK.
        - Creates a ``DecisionEvidence`` row for each ``evidence_id`` in
          ``payload.evidence_ids`` (Requirement 11.6).
        - Updates ``case.case_status`` to ``"DECIDED"`` (Requirement 11.3).
        - Inserts a ``DECISION_RECORDED`` CaseEvent via
          ``audit_service.insert_case_event`` (Requirement 11.3).
        - Writes an AuditLog for the Decision INSERT via
          ``audit_service.log_insert`` (Requirement 13.4).
        - Writes an AuditLog for the IntegrityCase UPDATE via
          ``audit_service.log_update`` (Requirement 13.4).
        - Does **not** commit — the caller owns the transaction boundary.

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        case_id: The primary key of the IntegrityCase.
        payload: ``DecisionCreate`` containing reviewer_id, decision_outcome,
            rationale, optional previous_decision_id, evidence_ids list, and
            actor_role.
        actor: Optional actor override (unused; actor info comes from
            ``payload``).

    Returns:
        ``DecisionOut`` reflecting the newly created Decision.
    """
    # ── Verify the case exists (404) ─────────────────────────────────────
    case = db.execute(
        select(IntegrityCase).where(IntegrityCase.case_id == case_id)
    ).scalars().first()
    if case is None:
        raise HTTPException(
            status_code=404, detail=f"IntegrityCase {case_id} not found"
        )

    # ── Guard: no final decision without a pending appeal (409) (Req 21.2) ──
    # Check if a final decision exists for this case.
    existing_final = db.execute(
        select(Decision).where(
            Decision.case_id == case_id,
            Decision.is_final == True,  # noqa: E712
        )
    ).scalars().first()

    if existing_final is not None:
        # Check if there is an appeal in APPEAL_PENDING status for this case.
        pending_appeal = db.execute(
            select(Appeal).where(
                Appeal.case_id == case_id,
                Appeal.appeal_status.in_(["SUBMITTED", "UNDER_REVIEW"]),
            )
        ).scalars().first()

        if pending_appeal is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"IntegrityCase {case_id} already has a final Decision "
                    "with no pending appeal. Use previous_decision_id to "
                    "record a superseding decision after the appeal is pending."
                ),
            )

    # ── Guard: validate previous_decision_id belongs to same case (422) ──
    if payload.previous_decision_id is not None:
        prev_decision = db.execute(
            select(Decision).where(
                Decision.decision_id == payload.previous_decision_id
            )
        ).scalars().first()

        if prev_decision is None or prev_decision.case_id != case_id:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"previous_decision_id {payload.previous_decision_id} "
                    f"does not belong to IntegrityCase {case_id}"
                ),
            )

    # ── Insert Decision record (Requirement 11.1) ─────────────────────────
    now = datetime.utcnow()
    decision = Decision(
        case_id=case_id,
        reviewer_id=payload.reviewer_id,
        previous_decision_id=payload.previous_decision_id,
        decision_outcome=payload.decision_outcome,
        rationale=payload.rationale,
        decided_at=now,
        is_final=True,
    )
    db.add(decision)
    # Flush to get the generated decision_id PK so we can use it for
    # DecisionEvidence rows and the audit log.
    db.flush()

    # ── Create DecisionEvidence rows (Requirement 11.6) ──────────────────
    for evidence_id in payload.evidence_ids:
        db.add(
            DecisionEvidence(
                decision_id=decision.decision_id,
                evidence_id=evidence_id,
            )
        )

    # ── Capture old case_status before mutation ───────────────────────────
    old_case_status = case.case_status

    # ── Update case status to DECIDED (Requirement 11.3) ─────────────────
    case.case_status = "DECIDED"

    # ── Build audit value snapshots ───────────────────────────────────────
    decision_new_values = {
        "decision_id": decision.decision_id,
        "case_id": case_id,
        "reviewer_id": payload.reviewer_id,
        "previous_decision_id": payload.previous_decision_id,
        "decision_outcome": payload.decision_outcome,
        "rationale": payload.rationale,
        "decided_at": now.isoformat(),
        "is_final": True,
    }

    case_old_values = {"case_status": old_case_status}
    case_new_values = {"case_status": "DECIDED"}

    # ── Insert DECISION_RECORDED CaseEvent (Requirement 11.3) ─────────────
    audit_service.insert_case_event(
        db=db,
        case_id=case_id,
        event_type="DECISION_RECORDED",
        actor_role=payload.actor_role,
        prev_status=old_case_status,
        new_status="DECIDED",
        details={"decision_id": decision.decision_id},
        actor_ref=payload.reviewer_id,
    )

    # ── Write AuditLog for Decision INSERT (Requirement 13.4) ─────────────
    audit_service.log_insert(
        db=db,
        entity_type="Decision",
        entity_id=str(decision.decision_id),
        new_values=decision_new_values,
        actor_role=payload.actor_role,
        actor_ref=payload.reviewer_id,
    )

    # ── Write AuditLog for IntegrityCase UPDATE (Requirement 13.4) ────────
    audit_service.log_update(
        db=db,
        entity_type="IntegrityCase",
        entity_id=case_id,
        old_values=case_old_values,
        new_values=case_new_values,
        actor_role=payload.actor_role,
        actor_ref=payload.reviewer_id,
    )

    return DecisionOut.model_validate(decision)


def get_decisions(db: Session, case_id: str) -> list[DecisionOut]:
    """Return all Decision records for an IntegrityCase ordered by
    ``decided_at`` descending (Requirement 11.2).

    Raises ``HTTPException`` with status 404 if the case is not found.

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        case_id: The primary key of the IntegrityCase.

    Returns:
        List of ``DecisionOut`` ordered by ``decided_at`` descending.
    """
    # ── Verify the case exists (404) ─────────────────────────────────────
    case = db.execute(
        select(IntegrityCase).where(IntegrityCase.case_id == case_id)
    ).scalars().first()
    if case is None:
        raise HTTPException(
            status_code=404, detail=f"IntegrityCase {case_id} not found"
        )

    # ── Query decisions ordered by decided_at descending ─────────────────
    stmt = (
        select(Decision)
        .where(Decision.case_id == case_id)
        .order_by(Decision.decided_at.desc())
    )
    decisions = db.execute(stmt).scalars().all()

    return [DecisionOut.model_validate(d) for d in decisions]
