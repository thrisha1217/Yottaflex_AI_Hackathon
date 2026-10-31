"""
backend/routers/evidence.py

Thin FastAPI router for the Evidence endpoints (Requirement 10).

Endpoints (mounted under ``/cases`` in main.py):
- ``POST /cases/{case_id}/evidence``   — add evidence item; HTTP 201
  (Requirements 10.1, 10.2)
- ``GET  /cases/{case_id}/evidence``   — list evidence ordered by added_at
  (Requirements 10.2, 10.3)
- ``DELETE /cases/{case_id}/evidence`` — explicitly rejected; HTTP 405
  (Requirement 10.5)
- ``PUT  /cases/{case_id}/evidence``   — explicitly rejected; HTTP 405
  (Requirement 10.5)

Routers are thin: call service, commit on success, return result.

Validates: Requirements 10.1, 10.2, 10.5
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.evidence import EvidenceItemCreate, EvidenceItemOut
from backend.services.evidence_service import add_evidence, get_evidence

router = APIRouter()


# ── POST /cases/{case_id}/evidence — add an evidence item ───────────────────


@router.post(
    "/{case_id}/evidence",
    response_model=EvidenceItemOut,
    status_code=201,
)
def create_evidence(
    case_id: str,
    payload: EvidenceItemCreate,
    db: Session = Depends(get_db),
) -> EvidenceItemOut:
    """Add an EvidenceItem to an IntegrityCase.

    Returns HTTP 201 with the created EvidenceItemOut on success.
    Returns HTTP 404 if the case does not exist (Requirement 10.6).

    Requirements 10.1 (endpoint exists and creates evidence item),
    10.2 (returns EvidenceItemOut).
    """
    result = add_evidence(db, case_id, payload)
    db.commit()
    return result


# ── GET /cases/{case_id}/evidence — list evidence items ─────────────────────


@router.get(
    "/{case_id}/evidence",
    response_model=list[EvidenceItemOut],
)
def list_evidence(
    case_id: str,
    db: Session = Depends(get_db),
) -> list[EvidenceItemOut]:
    """Return all EvidenceItem records for an IntegrityCase, ordered by
    ``added_at`` ascending.

    Returns HTTP 404 if the case does not exist (Requirement 10.6).

    Requirements 10.2 (returns list[EvidenceItemOut] ordered by added_at).
    """
    return get_evidence(db, case_id)


# ── DELETE /cases/{case_id}/evidence — explicitly rejected ──────────────────


@router.delete("/{case_id}/evidence")
def delete_evidence(case_id: str) -> None:  # noqa: ARG001
    """Evidence items are immutable — DELETE is not permitted.

    Requirement 10.5 (evidence items cannot be deleted or modified).
    """
    raise HTTPException(
        status_code=405,
        detail="Method not allowed. Evidence items are immutable.",
    )


# ── PUT /cases/{case_id}/evidence — explicitly rejected ─────────────────────


@router.put("/{case_id}/evidence")
def put_evidence(case_id: str) -> None:  # noqa: ARG001
    """Evidence items are immutable — PUT is not permitted.

    Requirement 10.5 (evidence items cannot be deleted or modified).
    """
    raise HTTPException(
        status_code=405,
        detail="Method not allowed. Evidence items are immutable.",
    )
