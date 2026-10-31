"""
backend/services/analytics_service.py

Service layer for the Analytics Engine endpoints (Requirement 19).
Each function executes an aggregate SQL query via SQLAlchemy and returns
the appropriate Pydantic response schema.

Functions
---------
summary                  – Req 19.1: high-level counts
cases_over_time          – Req 19.2: monthly IntegrityCase counts
outcomes_by_program      – Req 19.3: decision outcomes grouped by programme
top_assessments          – Req 19.4: top 10 assessments by case count
similarity_distribution  – Req 19.5: SimilarityReport counts per score bucket
"""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import case, func, text
from sqlalchemy.orm import Session

from backend.config import settings

from backend.config import settings
from backend.models.assessment import Assessment
from backend.models.decision import Decision
from backend.models.integrity_case import IntegrityCase
from backend.models.learner import Learner
from backend.models.similarity_report import SimilarityReport
from backend.models.submission import Submission
from backend.models.appeal import Appeal
from backend.schemas.analytics import (
    AssessmentCaseCount,
    CasesOverTimeOut,
    MonthlyCaseCount,
    OutcomesByProgramOut,
    ProgramOutcomes,
    ScoreBucket,
    SimilarityDistributionOut,
    SummaryOut,
    TopAssessmentsOut,
)


# ---------------------------------------------------------------------------
# 19.1  Summary counts
# ---------------------------------------------------------------------------


def summary(db: Session) -> SummaryOut:
    """Return high-level aggregate counts across the system.

    Validates: Requirements 19.1
    """
    from backend.models.appeal import Appeal  # local to avoid circular at module level

    total_submissions = db.query(func.count(Submission.submission_id)).scalar() or 0
    flagged_submissions = (
        db.query(func.count(SimilarityReport.report_id))
        .filter(SimilarityReport.review_required.is_(True))
        .scalar()
        or 0
    )
    total_cases = db.query(func.count(IntegrityCase.case_id)).scalar() or 0
    total_decisions = db.query(func.count(Decision.decision_id)).scalar() or 0
    total_appeals = db.query(func.count(Appeal.appeal_id)).scalar() or 0
    return SummaryOut(
        total_submissions=total_submissions,
        flagged_submissions=flagged_submissions,
        total_cases=total_cases,
        total_decisions=total_decisions,
        total_appeals=total_appeals,
    )


# ---------------------------------------------------------------------------
# 19.5  Similarity score distribution
# ---------------------------------------------------------------------------


def similarity_distribution(db: Session) -> SimilarityDistributionOut:
    """Return SimilarityReport counts per 10-point score bucket.

    Bucket label format: "0-9", "10-19", …, "90-100".

    Validates: Requirements 19.5
    """
    floor_expr = (func.floor(SimilarityReport.similarity_score / 10) * 10).label(
        "bucket_start"
    )
    rows = (
        db.query(floor_expr, func.count(SimilarityReport.report_id).label("count"))
        .group_by(floor_expr)
        .order_by(floor_expr)
        .all()
    )
    buckets = [
        ScoreBucket(
            bucket=f"{int(r.bucket_start)}-{int(r.bucket_start) + 9}",
            count=r.count,
        )
        for r in rows
    ]
    return SimilarityDistributionOut(data=buckets)


# ---------------------------------------------------------------------------
# 19.2  Cases over time
# ---------------------------------------------------------------------------


def cases_over_time(
    db: Session,
    from_date: date | None,
    to_date: date | None,
) -> CasesOverTimeOut:
    """Return monthly IntegrityCase counts, optionally filtered by date range.

    Validates: Requirements 19.2

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    from_date:
        Optional inclusive lower bound on ``IntegrityCase.opened_at``.
    to_date:
        Optional inclusive upper bound on ``IntegrityCase.opened_at``.

    Raises
    ------
    HTTPException (422):
        When both dates are supplied but ``from_date > to_date``.
    """
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(
            status_code=422,
            detail="from_date must not be later than to_date",
        )

    _is_sqlite = settings.DATABASE_URL.startswith("sqlite")
    if _is_sqlite:
        month_label = func.strftime("%Y-%m", IntegrityCase.opened_at).label("month")
    else:
        month_label = func.date_format(IntegrityCase.opened_at, "%Y-%m").label("month")

    query = (
        db.query(month_label, func.count().label("count"))
        .group_by(month_label)
        .order_by(month_label)
    )

    if from_date is not None and to_date is not None:
        query = query.filter(
            IntegrityCase.opened_at.between(from_date, to_date)
        )
    elif from_date is not None:
        query = query.filter(IntegrityCase.opened_at >= from_date)
    elif to_date is not None:
        query = query.filter(IntegrityCase.opened_at <= to_date)

    rows = query.all()
    return CasesOverTimeOut(
        data=[MonthlyCaseCount(month=row.month, count=row.count) for row in rows]
    )


# ---------------------------------------------------------------------------
# 19.3  Outcomes by programme
# ---------------------------------------------------------------------------


def outcomes_by_program(db: Session) -> OutcomesByProgramOut:
    """Return decision-outcome counts grouped by learner programme.

    JOIN chain: Decision → IntegrityCase → SimilarityReport → Submission → Learner

    Validates: Requirements 19.3
    """
    no_violation_count = func.sum(
        case((Decision.decision_outcome == "NO_VIOLATION", 1), else_=0)
    ).label("no_violation")
    violation_count = func.sum(
        case((Decision.decision_outcome == "VIOLATION", 1), else_=0)
    ).label("violation")
    inconclusive_count = func.sum(
        case((Decision.decision_outcome == "INCONCLUSIVE", 1), else_=0)
    ).label("inconclusive")

    rows = (
        db.query(
            Learner.program,
            no_violation_count,
            violation_count,
            inconclusive_count,
        )
        .join(IntegrityCase, Decision.case_id == IntegrityCase.case_id)
        .join(SimilarityReport, IntegrityCase.report_id == SimilarityReport.report_id)
        .join(Submission, SimilarityReport.submission_id == Submission.submission_id)
        .join(Learner, Submission.learner_id == Learner.learner_id)
        .group_by(Learner.program)
        .all()
    )

    return OutcomesByProgramOut(
        data=[
            ProgramOutcomes(
                program=row.program or "",
                NO_VIOLATION=int(row.no_violation or 0),
                VIOLATION=int(row.violation or 0),
                INCONCLUSIVE=int(row.inconclusive or 0),
            )
            for row in rows
        ]
    )


# ---------------------------------------------------------------------------
# 19.4  Top assessments
# ---------------------------------------------------------------------------


def top_assessments(db: Session) -> TopAssessmentsOut:
    """Return the top 10 assessments ranked by linked IntegrityCase count.

    JOIN chain: Assessment → Submission → SimilarityReport → IntegrityCase

    Validates: Requirements 19.4
    """
    case_count_col = func.count(IntegrityCase.case_id).label("case_count")

    rows = (
        db.query(
            Assessment.assessment_id,
            Assessment.title,
            case_count_col,
        )
        .join(Submission, Assessment.assessment_id == Submission.assessment_id)
        .join(SimilarityReport, Submission.submission_id == SimilarityReport.submission_id)
        .join(IntegrityCase, SimilarityReport.report_id == IntegrityCase.report_id)
        .group_by(Assessment.assessment_id, Assessment.title)
        .order_by(case_count_col.desc())
        .limit(10)
        .all()
    )

    return TopAssessmentsOut(
        data=[
            AssessmentCaseCount(
                assessment_id=row.assessment_id,
                title=row.title,
                case_count=row.case_count,
            )
            for row in rows
        ]
    )
