"""
backend/services/evidence_service.py

Service layer for evidence management endpoints (Requirement 10).

All functions receive the caller's SQLAlchemy ``Session`` and perform
mutations that write rows via ``db.add()`` **without committing**. The
transaction boundary is owned by the router layer — services never call
``db.commit()`` or ``db.rollback()``. This keeps EvidenceItem, CaseEvent,
and AuditLog writes in the same transaction so a failed rollback cleans up
the data and its audit trail together.

Requirements validated: 10.1, 10.2, 10.3, 10.4, 10.6
"""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.evidence_item import EvidenceItem
from backend.models.integrity_case import IntegrityCase
from backend.schemas.evidence import EvidenceItemCreate, EvidenceItemOut
from backend.services import audit_service


def add_evidence(
    db: Session,
    case_id: str,
    payload: EvidenceItemCreate,
    actor=None,
) -> EvidenceItemOut:
    """Add an EvidenceItem to an IntegrityCase (Requirement 10.1).

    Guards:
        - Case must exist (404 if not found) (Requirement 10.6).
        - If ``case_status = CLOSED``, the new EvidenceItem has
          ``is_material = False`` (Requirement 10.4).

    Inserts an ``EvidenceItem`` record, an ``EVIDENCE_ADDED`` CaseEvent
    (Requirement 10.3), and an AuditLog for the EvidenceItem INSERT
    (Requirement 13.4). Does **not** commit — the caller owns the
    transaction boundary.

    The ``evidence_id`` is generated as ``EVD-{count+1:06d}`` where
    ``count`` is the current number of EvidenceItem rows in the database.

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        case_id: The primary key of the IntegrityCase.
        payload: ``EvidenceItemCreate`` containing ``evidence_type``,
            ``description``, optional ``evidence_reference``,
            ``added_by_role``, optional ``added_by_ref``, and ``actor_role``.
        actor: Optional actor override (unused; actor info comes from
            ``payload``).

    Returns:
        ``EvidenceItemOut`` reflecting the newly created evidence item.
    """
    # ── Verify the case exists (404) (Requirement 10.6) ──────────────────
    case = db.execute(
        select(IntegrityCase).where(IntegrityCase.case_id == case_id)
    ).scalars().first()
    if case is None:
        raise HTTPException(
            status_code=404, detail=f"IntegrityCase {case_id} not found"
        )

    # ── Determine is_material based on case status (Requirement 10.4) ────
    is_material = case.case_status != "CLOSED"

    # ── Generate evidence_id: EVD-{count+1:06d} ──────────────────────────
    count = db.execute(
        select(func.count()).select_from(EvidenceItem)
    ).scalar_one()
    evidence_id = f"EVD-{count + 1:06d}"

    # ── Insert EvidenceItem record (Requirement 10.1) ───────────────────
    now = datetime.utcnow()
    evidence_item = EvidenceItem(
        evidence_id=evidence_id,
        case_id=case_id,
        evidence_type=payload.evidence_type,
        description=payload.description,
        evidence_reference=payload.evidence_reference,
        added_by_role=payload.added_by_role,
        added_by_ref=payload.added_by_ref,
        added_at=now,
        is_material=is_material,
    )
    db.add(evidence_item)
    # Flush to populate server-side defaults and ensure the row is visible
    # within the transaction for the return value and audit log.
    db.flush()

    new_values = {
        "evidence_id": evidence_id,
        "case_id": case_id,
        "evidence_type": payload.evidence_type,
        "description": payload.description,
        "evidence_reference": payload.evidence_reference,
        "added_by_role": payload.added_by_role,
        "added_by_ref": payload.added_by_ref,
        "added_at": now.isoformat(),
        "is_material": is_material,
    }

    # ── Insert EVIDENCE_ADDED CaseEvent (Requirement 10.3) ────────────────
    audit_service.insert_case_event(
        db=db,
        case_id=case_id,
        event_type="EVIDENCE_ADDED",
        actor_role=payload.actor_role,
        actor_ref=payload.added_by_ref,
    )

    # ── Write AuditLog for EvidenceItem INSERT (Requirement 13.4) ────────
    audit_service.log_insert(
        db=db,
        entity_type="EvidenceItem",
        entity_id=evidence_id,
        new_values=new_values,
        actor_role=payload.actor_role,
        actor_ref=payload.added_by_ref,
    )

    return EvidenceItemOut.model_validate(evidence_item)


def get_evidence(db: Session, case_id: str) -> list[EvidenceItemOut]:
    """Return all EvidenceItem records for an IntegrityCase, ordered by
    ``added_at`` ascending (Requirement 10.2).

    Raises ``HTTPException`` with status 404 if the case is not found
    (Requirement 10.6).

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        case_id: The primary key of the IntegrityCase.

    Returns:
        List of ``EvidenceItemOut`` ordered by ``added_at`` ascending.
    """
    # ── Verify the case exists (404) (Requirement 10.6) ──────────────────
    case = db.execute(
        select(IntegrityCase).where(IntegrityCase.case_id == case_id)
    ).scalars().first()
    if case is None:
        raise HTTPException(
            status_code=404, detail=f"IntegrityCase {case_id} not found"
        )

    # ── Query evidence items ordered by added_at ascending ───────────────
    stmt = (
        select(EvidenceItem)
        .where(EvidenceItem.case_id == case_id)
        .order_by(EvidenceItem.added_at.asc())
    )
    result = db.execute(stmt)
    evidence_items = result.scalars().all()

    return [EvidenceItemOut.model_validate(e) for e in evidence_items]
