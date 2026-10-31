"""
backend/routers/decisions.py

Thin FastAPI router for the Decision endpoints (Requirement 11).

Endpoints (mounted under ``/cases`` in main.py):
- ``POST /cases/{case_id}/decisions``                         — record a decision; HTTP 201
  (Requirements 11.1, 11.2)
- ``GET  /cases/{case_id}/decisions``                         — list decisions ordered by decided_at desc
  (Requirements 11.2)
- ``DELETE /cases/{case_id}/decisions/{decision_id}``         — explicitly rejected; HTTP 405
  (Requirement 11.5)
- ``PUT    /cases/{case_id}/decisions/{decision_id}``         — explicitly rejected; HTTP 405
  (Requirement 11.5)

Routers are thin: call service, commit on success, return result.

Validates: Requirements 11.1, 11.2, 11.5
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.decisions import DecisionCreate, DecisionOut
from backend.services.decision_service import create_decision, get_decisions

router = APIRouter()


# ── POST /cases/{case_id}/decisions — record a decision ─────────────────────


@router.post(
    "/{case_id}/decisions",
    response_model=DecisionOut,
    status_code=201,
)
def post_decision(
    case_id: str,
    payload: DecisionCreate,
    db: Session = Depends(get_db),
) -> DecisionOut:
    """Record a Decision for an IntegrityCase.

    Returns HTTP 201 with the created DecisionOut on success.
    Returns HTTP 404 if the case does not exist.
    Returns HTTP 409 if a final decision already exists with no pending appeal
    (Requirement 21.2).
    Returns HTTP 422 if previous_decision_id does not belong to this case
    (Requirement 11.4).

    Requirements 11.1 (endpoint exists and creates decision),
    11.2 (returns DecisionOut).
    """
    result = create_decision(db, case_id, payload)
    db.commit()
    return result


# ── GET /cases/{case_id}/decisions — list decisions ─────────────────────────


@router.get(
    "/{case_id}/decisions",
    response_model=list[DecisionOut],
)
def list_decisions(
    case_id: str,
    db: Session = Depends(get_db),
) -> list[DecisionOut]:
    """Return all Decision records for an IntegrityCase ordered by
    ``decided_at`` descending.

    Returns HTTP 404 if the case does not exist.

    Requirement 11.2 (returns list[DecisionOut] ordered by decided_at desc).
    """
    return get_decisions(db, case_id)


# ── DELETE /cases/{case_id}/decisions/{decision_id} — explicitly rejected ───


@router.delete("/{case_id}/decisions/{decision_id}")
def delete_decision(case_id: str, decision_id: int) -> None:  # noqa: ARG001
    """Decisions are immutable — DELETE is not permitted.

    Requirement 11.5 (decisions cannot be deleted or modified).
    """
    raise HTTPException(
        status_code=405,
        detail="Method not allowed. Decisions are immutable.",
    )


# ── PUT /cases/{case_id}/decisions/{decision_id} — explicitly rejected ───────


@router.put("/{case_id}/decisions/{decision_id}")
def put_decision(case_id: str, decision_id: int) -> None:  # noqa: ARG001
    """Decisions are immutable — PUT is not permitted.

    Requirement 11.5 (decisions cannot be deleted or modified).
    """
    raise HTTPException(
        status_code=405,
        detail="Method not allowed. Decisions are immutable.",
    )
