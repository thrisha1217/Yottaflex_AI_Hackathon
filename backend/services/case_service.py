"""
backend/services/case_service.py

Service layer for submission and similarity report queries (Requirement 7).

All functions receive the caller's SQLAlchemy ``Session`` and perform
read-only queries — they never commit or rollback. The transaction
boundary is owned by the router layer, consistent with the design's
"services own business logic but not the transaction" contract.

Requirements validated: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, selectinload

from backend.models.case_reviewer import CaseReviewer
from backend.models.integrity_case import IntegrityCase
from backend.models.reviewer import Reviewer
from backend.models.similarity_report import SimilarityReport
from backend.models.submission import Submission
from backend.schemas.cases import (
    CaseDetail,
    CaseEventOut,
    CaseReviewerSummary,
    CaseStatus,
    CaseStatusUpdate,
    CaseSummary,
    DecisionSummary,
    PaginatedCases,
    Priority,
)
from backend.schemas.submissions import (
    PaginatedSubmissions,
    RuleSummary,
    SimilarityReportDetail,
    SimilarityReportSummary,
    SubmissionDetail,
    SubmissionSummary,
)
from backend.schemas.reviewers import (
    CaseReviewerCreate,
    CaseReviewerOut,
    ConflictUpdate,
    PaginatedReviewers,
    ReviewerOut,
)
from backend.services import audit_service


# ── Submission queries ──────────────────────────────────────────────────────


def get_submissions(
    db: Session,
    flagged: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedSubmissions:
    """Return a paginated list of submissions, optionally filtered to flagged.

    When ``flagged`` is ``True``, only submissions whose linked
    SimilarityReport has ``review_required = True`` are returned
    (Requirement 7.3).

    Each ``SubmissionSummary`` is populated with ``similarity_score`` and
    ``review_required`` from the linked SimilarityReport when one exists;
    otherwise those fields are ``None`` (a submission may not yet have a
    report attached).

    Pagination uses 1-based ``page`` and ``page_size``; the response envelope
    includes ``total_count``, ``page``, and ``page_size`` (Requirement 7.4).

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        flagged: If ``True``, return only flagged submissions.
        page: 1-based page number.
        page_size: Maximum number of items per page.

    Returns:
        ``PaginatedSubmissions`` envelope with items, total_count, page,
        and page_size.
    """
    offset = (page - 1) * page_size

    # ── Total count (before paging) ───────────────────────────────────────
    count_stmt = select(func.count()).select_from(Submission)
    if flagged:
        count_stmt = (
            count_stmt.join(SimilarityReport)
            .where(SimilarityReport.review_required == True)  # noqa: E712
        )
    total_count = db.execute(count_stmt).scalar_one()

    # ── Page query — eagerly load the linked report to avoid N+1 ─────────
    stmt = select(Submission).options(selectinload(Submission.report))
    if flagged:
        stmt = (
            stmt.join(SimilarityReport)
            .where(SimilarityReport.review_required == True)  # noqa: E712
        )
    stmt = stmt.offset(offset).limit(page_size)

    result = db.execute(stmt)
    submissions = result.scalars().all()

    # ── Build summaries with report-derived fields ───────────────────────
    items: list[SubmissionSummary] = []
    for sub in submissions:
        report = sub.report
        items.append(
            SubmissionSummary(
                submission_id=sub.submission_id,
                learner_id=sub.learner_id,
                assessment_id=sub.assessment_id,
                attempt_no=sub.attempt_no,
                submitted_at=sub.submitted_at,
                status=sub.status,
                similarity_score=float(report.similarity_score) if report else None,
                review_required=report.review_required if report else None,
            )
        )

    return PaginatedSubmissions(
        items=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
    )


def get_submission_detail(db: Session, submission_id: str) -> SubmissionDetail:
    """Return a single submission with its linked SimilarityReport (Requirement 7.2).

    Raises ``HTTPException`` with status 404 if the submission is not found
    (Requirement 7.5).

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        submission_id: The primary key of the submission to retrieve.

    Returns:
        ``SubmissionDetail`` including content fields and the nested
        ``SimilarityReportSummary`` when a report is linked.
    """
    stmt = (
        select(Submission)
        .options(selectinload(Submission.report))
        .where(Submission.submission_id == submission_id)
    )
    result = db.execute(stmt)
    submission = result.scalars().first()

    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    report = submission.report
    report_summary: SimilarityReportSummary | None = None
    if report:
        report_summary = SimilarityReportSummary(
            report_id=report.report_id,
            submission_id=report.submission_id,
            similarity_score=float(report.similarity_score),
            review_required=report.review_required,
            report_status=report.report_status,
            generated_at=report.generated_at,
        )

    return SubmissionDetail(
        submission_id=submission.submission_id,
        learner_id=submission.learner_id,
        assessment_id=submission.assessment_id,
        attempt_no=submission.attempt_no,
        submitted_at=submission.submitted_at,
        status=submission.status,
        similarity_score=float(report.similarity_score) if report else None,
        review_required=report.review_required if report else None,
        content_reference=submission.content_reference,
        content_hash=submission.content_hash,
        report=report_summary,
    )


# ── Similarity report queries ────────────────────────────────────────────────


def get_similarity_report(db: Session, report_id: str) -> SimilarityReportDetail:
    """Return the full similarity report including the linked IntegrityRule
    (Requirement 7.6).

    Raises ``HTTPException`` with status 404 if the report is not found.

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        report_id: The primary key of the SimilarityReport to retrieve.

    Returns:
        ``SimilarityReportDetail`` including ``report_no``,
        ``matched_source_count``, ``rule_id``, and the nested ``RuleSummary``
        when a rule is linked.
    """
    stmt = (
        select(SimilarityReport)
        .options(selectinload(SimilarityReport.rule))
        .where(SimilarityReport.report_id == report_id)
    )
    result = db.execute(stmt)
    report = result.scalars().first()

    if report is None:
        raise HTTPException(status_code=404, detail="Similarity report not found")

    rule = report.rule
    rule_summary: RuleSummary | None = None
    if rule:
        rule_summary = RuleSummary(
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            action_type=rule.action_type,
        )

    return SimilarityReportDetail(
        report_id=report.report_id,
        submission_id=report.submission_id,
        similarity_score=float(report.similarity_score),
        review_required=report.review_required,
        report_status=report.report_status,
        generated_at=report.generated_at,
        report_no=report.report_no,
        matched_source_count=report.matched_source_count,
        rule_id=report.rule_id,
        rule=rule_summary,
    )


# ── Case queries and mutations ──────────────────────────────────────────────


# Valid status transitions for the IntegrityCase lifecycle (Requirement 8.6).
# CLOSED is terminal — no transitions out of it are allowed.
VALID_STATUS_TRANSITIONS: dict[CaseStatus, set[CaseStatus]] = {
    CaseStatus.OPEN: {
        CaseStatus.UNDER_REVIEW,
        CaseStatus.AWAITING_INFORMATION,
        CaseStatus.CLOSED,
    },
    CaseStatus.UNDER_REVIEW: {
        CaseStatus.AWAITING_INFORMATION,
        CaseStatus.DECIDED,
        CaseStatus.CLOSED,
    },
    CaseStatus.AWAITING_INFORMATION: {
        CaseStatus.UNDER_REVIEW,
        CaseStatus.CLOSED,
    },
    CaseStatus.DECIDED: {
        CaseStatus.APPEAL_PENDING,
        CaseStatus.CLOSED,
    },
    CaseStatus.APPEAL_PENDING: {
        CaseStatus.DECIDED,
        CaseStatus.CLOSED,
    },
    CaseStatus.CLOSED: set(),  # terminal state
}


def _build_report_summary(report: SimilarityReport) -> SimilarityReportSummary:
    """Build a ``SimilarityReportSummary`` from a loaded ORM report."""
    return SimilarityReportSummary(
        report_id=report.report_id,
        submission_id=report.submission_id,
        similarity_score=float(report.similarity_score),
        review_required=report.review_required,
        report_status=report.report_status,
        generated_at=report.generated_at,
    )


def _build_case_detail(case: IntegrityCase) -> CaseDetail:
    """Build a ``CaseDetail`` from an ``IntegrityCase`` with eagerly loaded
    relationships (report, reviewers, decisions, events).

    The caller is responsible for ensuring the relationships are loaded
    (via ``selectinload``) to avoid N+1 queries.
    """
    # ── Report summary (every case has a linked report) ─────────────────
    report_summary = _build_report_summary(case.report)

    # ── Reviewer summaries ───────────────────────────────────────────────
    reviewers = [CaseReviewerSummary.model_validate(r) for r in case.reviewers]

    # ── Decision summary — latest final decision if present ──────────────
    decision_summary: DecisionSummary | None = None
    final_decisions = [d for d in case.decisions if d.is_final]
    if final_decisions:
        latest = max(final_decisions, key=lambda d: d.decided_at)
        decision_summary = DecisionSummary.model_validate(latest)

    # ── Event summaries (already ordered by occurred_at via relationship) ─
    events = [CaseEventOut.model_validate(e) for e in case.events]

    # ── Computed has_conflict ────────────────────────────────────────────
    has_conflict = any(r.conflict_status == "CONFLICT" for r in case.reviewers)

    return CaseDetail(
        case_id=case.case_id,
        case_status=CaseStatus(case.case_status),
        priority=case.priority,
        opened_at=case.opened_at,
        closed_at=case.closed_at,
        has_conflict=has_conflict,
        report_summary=report_summary,
        reviewers=reviewers,
        decision_summary=decision_summary,
        events=events,
    )


def get_cases(
    db: Session,
    status: CaseStatus | None = None,
    priority: Priority | None = None,
    assigned_reviewer_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedCases:
    """Return a paginated, filtered list of IntegrityCase records
    (Requirements 8.1, 8.7).

    Supports filtering by ``status`` (CaseStatus), ``priority``, and
    ``assigned_reviewer_id``. Each ``CaseSummary`` includes the computed
    ``has_conflict`` field — ``True`` when any CaseReviewer on the case has
    ``conflict_status = CONFLICT``.

    Pagination uses 1-based ``page`` and ``page_size``; the response envelope
    includes ``total_count``, ``page``, and ``page_size``.

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        status: Optional CaseStatus filter.
        priority: Optional Priority filter.
        assigned_reviewer_id: Optional reviewer_id filter — returns only
            cases that have a CaseReviewer assignment for this reviewer.
        page: 1-based page number.
        page_size: Maximum number of items per page.

    Returns:
        ``PaginatedCases`` envelope with items, total_count, page, and
        page_size.
    """
    offset = (page - 1) * page_size

    # ── Build a reusable subquery for the assigned_reviewer_id filter ────
    reviewer_subquery = None
    if assigned_reviewer_id is not None:
        reviewer_subquery = exists().where(
            CaseReviewer.case_id == IntegrityCase.case_id,
            CaseReviewer.reviewer_id == assigned_reviewer_id,
        )

    # ── Total count (before paging) ───────────────────────────────────────
    count_stmt = select(func.count()).select_from(IntegrityCase)
    if status is not None:
        count_stmt = count_stmt.where(IntegrityCase.case_status == status)
    if priority is not None:
        count_stmt = count_stmt.where(IntegrityCase.priority == priority)
    if reviewer_subquery is not None:
        count_stmt = count_stmt.where(reviewer_subquery)
    total_count = db.execute(count_stmt).scalar_one()

    # ── Page query — eagerly load reviewers to compute has_conflict ──────
    stmt = select(IntegrityCase).options(selectinload(IntegrityCase.reviewers))
    if status is not None:
        stmt = stmt.where(IntegrityCase.case_status == status)
    if priority is not None:
        stmt = stmt.where(IntegrityCase.priority == priority)
    if reviewer_subquery is not None:
        stmt = stmt.where(reviewer_subquery)
    stmt = stmt.offset(offset).limit(page_size)

    result = db.execute(stmt)
    cases = result.scalars().all()

    # ── Build summaries with computed has_conflict ──────────────────────
    items: list[CaseSummary] = []
    for case in cases:
        has_conflict = any(r.conflict_status == "CONFLICT" for r in case.reviewers)
        items.append(
            CaseSummary(
                case_id=case.case_id,
                case_status=CaseStatus(case.case_status),
                priority=case.priority,
                opened_at=case.opened_at,
                closed_at=case.closed_at,
                has_conflict=has_conflict,
            )
        )

    return PaginatedCases(
        items=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
    )


def get_case_detail(db: Session, case_id: str) -> CaseDetail:
    """Return the full IntegrityCase record including linked SimilarityReport
    summary, assigned reviewers, decision summary if present, and events
    (Requirement 8.2).

    Raises ``HTTPException`` with status 404 if the case is not found
    (Requirement 8.5).

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        case_id: The primary key of the IntegrityCase to retrieve.

    Returns:
        ``CaseDetail`` including report_summary, reviewers,
        decision_summary, and events.
    """
    stmt = (
        select(IntegrityCase)
        .options(
            selectinload(IntegrityCase.report),
            selectinload(IntegrityCase.reviewers),
            selectinload(IntegrityCase.decisions),
            selectinload(IntegrityCase.events),
        )
        .where(IntegrityCase.case_id == case_id)
    )
    result = db.execute(stmt)
    case = result.scalars().first()

    if case is None:
        raise HTTPException(
            status_code=404, detail=f"IntegrityCase {case_id} not found"
        )

    return _build_case_detail(case)


def update_case_status(
    db: Session,
    case_id: str,
    payload: CaseStatusUpdate,
    actor=None,
) -> CaseDetail:
    """Update the ``case_status`` of an IntegrityCase (Requirement 8.3).

    Inserts a ``STATUS_CHANGED`` CaseEvent recording the previous and new
    status (Requirement 8.4), and writes an AuditLog for the IntegrityCase
    UPDATE via ``audit_service.log_update`` (Requirement 13.4).

    Enforces valid status transitions; raises ``HTTPException`` with status
    422 on invalid transition (Requirement 8.6). Raises 404 if the case is
    not found (Requirement 8.5).

    Does **not** commit — the caller owns the transaction boundary.

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        case_id: The primary key of the IntegrityCase to update.
        payload: ``CaseStatusUpdate`` containing the new ``case_status``,
            ``actor_role``, and optional ``actor_ref``.
        actor: Optional actor override (unused; actor info comes from
            ``payload``).

    Returns:
        ``CaseDetail`` reflecting the updated case state.
    """
    # ── Load the case with relationships for the return value ────────────
    stmt = (
        select(IntegrityCase)
        .options(
            selectinload(IntegrityCase.report),
            selectinload(IntegrityCase.reviewers),
            selectinload(IntegrityCase.decisions),
            selectinload(IntegrityCase.events),
        )
        .where(IntegrityCase.case_id == case_id)
    )
    result = db.execute(stmt)
    case = result.scalars().first()

    if case is None:
        raise HTTPException(
            status_code=404, detail=f"IntegrityCase {case_id} not found"
        )

    # ── Validate status transition (Requirement 8.6) ─────────────────────
    current_status = CaseStatus(case.case_status)
    new_status = payload.case_status

    allowed = VALID_STATUS_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid status transition from {current_status.value} "
                f"to {new_status.value}"
            ),
        )

    # ── Capture old values before mutation ──────────────────────────────
    old_values = {
        "case_status": case.case_status,
        "closed_at": case.closed_at.isoformat() if case.closed_at else None,
    }

    # ── Apply the update ──────────────────────────────────────────────────
    case.case_status = new_status.value

    # Set closed_at when transitioning to CLOSED
    if new_status == CaseStatus.CLOSED and case.closed_at is None:
        case.closed_at = datetime.utcnow()

    new_values = {
        "case_status": case.case_status,
        "closed_at": case.closed_at.isoformat() if case.closed_at else None,
    }

    # ── Insert STATUS_CHANGED CaseEvent (Requirement 8.4) ─────────────────
    audit_service.insert_case_event(
        db=db,
        case_id=case_id,
        event_type="STATUS_CHANGED",
        actor_role=payload.actor_role,
        prev_status=current_status.value,
        new_status=new_status.value,
        actor_ref=payload.actor_ref,
    )

    # ── Write AuditLog for IntegrityCase UPDATE (Requirement 13.4) ───────
    audit_service.log_update(
        db=db,
        entity_type="IntegrityCase",
        entity_id=case_id,
        old_values=old_values,
        new_values=new_values,
        actor_role=payload.actor_role,
        actor_ref=payload.actor_ref,
    )

    # ── Return CaseDetail (without committing) ───────────────────────────
    return _build_case_detail(case)


# ── Reviewer assignment and conflict operations ──────────────────────────────


def assign_reviewer(
    db: Session,
    case_id: str,
    payload: CaseReviewerCreate,
    actor=None,
) -> CaseReviewerOut:
    """Assign a Reviewer to an IntegrityCase (Requirement 9.1).

    Guards:
        - Case must exist (404 if not found).
        - Reviewer must have ``status = ACTIVE`` (422 if INACTIVE)
          (Requirement 21.3).
        - Reviewer must not have an active CONFLICT on the same case
          (409 if they do) (Requirement 9.5).

    Inserts a ``CaseReviewer`` record, a ``REVIEWER_ASSIGNED`` CaseEvent,
    and an AuditLog for the CaseReviewer INSERT. Does **not** commit — the
    caller owns the transaction boundary.

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        case_id: The primary key of the IntegrityCase.
        payload: ``CaseReviewerCreate`` containing ``reviewer_id``,
            ``assignment_role``, and ``actor_role``.
        actor: Optional actor override (unused; actor info comes from
            ``payload``).

    Returns:
        ``CaseReviewerOut`` reflecting the newly created assignment.
    """
    # ── Verify the case exists (404) ─────────────────────────────────────
    case = db.execute(
        select(IntegrityCase).where(IntegrityCase.case_id == case_id)
    ).scalars().first()
    if case is None:
        raise HTTPException(
            status_code=404, detail=f"IntegrityCase {case_id} not found"
        )

    # ── Verify the reviewer exists and is ACTIVE ────────────────────────
    reviewer = db.execute(
        select(Reviewer).where(Reviewer.reviewer_id == payload.reviewer_id)
    ).scalars().first()
    if reviewer is None:
        raise HTTPException(
            status_code=404,
            detail=f"Reviewer {payload.reviewer_id} not found",
        )

    if reviewer.status != "ACTIVE":
        raise HTTPException(
            status_code=422,
            detail=f"Reviewer {payload.reviewer_id} is not active",
        )

    # ── Check for active CONFLICT on same case (409) ────────────────────
    existing_conflict = db.execute(
        select(CaseReviewer).where(
            CaseReviewer.case_id == case_id,
            CaseReviewer.reviewer_id == payload.reviewer_id,
            CaseReviewer.conflict_status == "CONFLICT",
        )
    ).scalars().first()
    if existing_conflict is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Reviewer {payload.reviewer_id} has an active conflict "
                f"on case {case_id}"
            ),
        )

    # ── Insert CaseReviewer record ──────────────────────────────────────
    now = datetime.utcnow()
    assignment = CaseReviewer(
        case_id=case_id,
        reviewer_id=payload.reviewer_id,
        assignment_role=payload.assignment_role,
        assigned_at=now,
        conflict_status="PENDING",
    )
    db.add(assignment)
    # Flush to populate the autoincrement assignment_id for the audit log.
    db.flush()

    new_values = {
        "assignment_id": assignment.assignment_id,
        "case_id": case_id,
        "reviewer_id": payload.reviewer_id,
        "assignment_role": payload.assignment_role,
        "assigned_at": now.isoformat(),
        "unassigned_at": None,
        "conflict_status": "PENDING",
        "conflict_reason": None,
    }

    # ── Insert REVIEWER_ASSIGNED CaseEvent ───────────────────────────────
    audit_service.insert_case_event(
        db=db,
        case_id=case_id,
        event_type="REVIEWER_ASSIGNED",
        actor_role=payload.actor_role,
    )

    # ── Write AuditLog for CaseReviewer INSERT (Requirement 13.4) ────────
    audit_service.log_insert(
        db=db,
        entity_type="CaseReviewer",
        entity_id=str(assignment.assignment_id),
        new_values=new_values,
        actor_role=payload.actor_role,
    )

    return CaseReviewerOut.model_validate(assignment)


def update_conflict(
    db: Session,
    case_id: str,
    assignment_id: int,
    payload: ConflictUpdate,
    actor=None,
) -> CaseReviewerOut:
    """Update the ``conflict_status`` of a CaseReviewer to ``CONFLICT``
    (Requirement 9.2).

    Guards:
        - Case must exist (404 if not found).
        - Assignment must exist and belong to the case (404 if not found).
        - Case must not be ``CLOSED`` (422 if CLOSED) (Requirement 21.4).

    Sets ``conflict_status = CONFLICT``, sets ``unassigned_at`` to the
    current timestamp, inserts a ``REVIEWER_CONFLICT_DECLARED`` CaseEvent
    (Requirement 9.4), and writes an AuditLog for the CaseReviewer UPDATE.
    Does **not** commit.

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        case_id: The primary key of the IntegrityCase.
        assignment_id: The primary key of the CaseReviewer record.
        payload: ``ConflictUpdate`` containing ``conflict_status``,
            optional ``conflict_reason``, ``actor_role``, and optional
            ``actor_ref``.
        actor: Optional actor override (unused; actor info comes from
            ``payload``).

    Returns:
        ``CaseReviewerOut`` reflecting the updated assignment.
    """
    # ── Verify the case exists (404) ─────────────────────────────────────
    case = db.execute(
        select(IntegrityCase).where(IntegrityCase.case_id == case_id)
    ).scalars().first()
    if case is None:
        raise HTTPException(
            status_code=404, detail=f"IntegrityCase {case_id} not found"
        )

    # ── Guard: case must not be CLOSED (422) ──────────────────────────────
    if case.case_status == "CLOSED":
        raise HTTPException(
            status_code=422,
            detail=(
                f"Cannot declare a conflict on a CLOSED case ({case_id})"
            ),
        )

    # ── Verify the assignment exists and belongs to the case (404) ──────
    assignment = db.execute(
        select(CaseReviewer).where(
            CaseReviewer.assignment_id == assignment_id,
            CaseReviewer.case_id == case_id,
        )
    ).scalars().first()
    if assignment is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"CaseReviewer assignment {assignment_id} not found "
                f"for case {case_id}"
            ),
        )

    # ── Capture old values before mutation ──────────────────────────────
    old_values = {
        "assignment_id": assignment.assignment_id,
        "case_id": assignment.case_id,
        "reviewer_id": assignment.reviewer_id,
        "assignment_role": assignment.assignment_role,
        "assigned_at": assignment.assigned_at.isoformat()
        if assignment.assigned_at
        else None,
        "unassigned_at": assignment.unassigned_at.isoformat()
        if assignment.unassigned_at
        else None,
        "conflict_status": assignment.conflict_status,
        "conflict_reason": assignment.conflict_reason,
    }

    # ── Apply the update ──────────────────────────────────────────────────
    now = datetime.utcnow()
    assignment.conflict_status = "CONFLICT"
    assignment.unassigned_at = now
    if payload.conflict_reason is not None:
        assignment.conflict_reason = payload.conflict_reason

    new_values = {
        "assignment_id": assignment.assignment_id,
        "case_id": assignment.case_id,
        "reviewer_id": assignment.reviewer_id,
        "assignment_role": assignment.assignment_role,
        "assigned_at": assignment.assigned_at.isoformat()
        if assignment.assigned_at
        else None,
        "unassigned_at": assignment.unassigned_at.isoformat()
        if assignment.unassigned_at
        else None,
        "conflict_status": assignment.conflict_status,
        "conflict_reason": assignment.conflict_reason,
    }

    # ── Insert REVIEWER_CONFLICT_DECLARED CaseEvent (Requirement 9.4) ─────
    audit_service.insert_case_event(
        db=db,
        case_id=case_id,
        event_type="REVIEWER_CONFLICT_DECLARED",
        actor_role=payload.actor_role,
        actor_ref=payload.actor_ref,
    )

    # ── Write AuditLog for CaseReviewer UPDATE (Requirement 13.4) ────────
    audit_service.log_update(
        db=db,
        entity_type="CaseReviewer",
        entity_id=str(assignment.assignment_id),
        old_values=old_values,
        new_values=new_values,
        actor_role=payload.actor_role,
        actor_ref=payload.actor_ref,
    )

    return CaseReviewerOut.model_validate(assignment)


def get_reviewers(
    db: Session,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedReviewers:
    """Return a paginated list of active Reviewer records (Requirement 9.6).

    Only reviewers with ``status = ACTIVE`` are returned. Pagination uses
    1-based ``page`` and ``page_size``; the response envelope includes
    ``total_count``, ``page``, and ``page_size``.

    Args:
        db: Active SQLAlchemy session (caller's transaction).
        page: 1-based page number.
        page_size: Maximum number of items per page.

    Returns:
        ``PaginatedReviewers`` envelope with items, total_count, page, and
        page_size.
    """
    offset = (page - 1) * page_size

    # ── Total count of active reviewers (before paging) ─────────────────
    total_count = db.execute(
        select(func.count())
        .select_from(Reviewer)
        .where(Reviewer.status == "ACTIVE")
    ).scalar_one()

    # ── Page query ────────────────────────────────────────────────────────
    stmt = (
        select(Reviewer)
        .where(Reviewer.status == "ACTIVE")
        .offset(offset)
        .limit(page_size)
    )
    reviewers = db.execute(stmt).scalars().all()

    items = [ReviewerOut.model_validate(r) for r in reviewers]

    return PaginatedReviewers(
        items=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
    )
