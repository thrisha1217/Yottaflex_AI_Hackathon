"""
backend/routers/analytics.py

FastAPI router for the Analytics Engine aggregate-metrics endpoints
(Requirement 19).

Endpoints
---------
GET /analytics/summary              – Req 19.1
GET /analytics/cases-over-time      – Req 19.2
GET /analytics/outcomes-by-program  – Req 19.3
GET /analytics/top-assessments      – Req 19.4
GET /analytics/similarity-distribution – Req 19.5
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.analytics import (
    CasesOverTimeOut,
    OutcomesByProgramOut,
    SimilarityDistributionOut,
    SummaryOut,
    TopAssessmentsOut,
)
from backend.services import analytics_service

router = APIRouter(tags=["Analytics"])


@router.get(
    "/summary",
    response_model=SummaryOut,
    summary="High-level aggregate counts (submissions, cases, decisions, appeals)",
)
def get_summary(db: Session = Depends(get_db)) -> SummaryOut:
    """Return total counts for Submission, flagged SimilarityReport,
    IntegrityCase, Decision, and Appeal records.

    Validates: Requirements 19.1
    """
    return analytics_service.summary(db)


@router.get(
    "/similarity-distribution",
    response_model=SimilarityDistributionOut,
    summary="SimilarityReport counts per 10-point score bucket",
)
def get_similarity_distribution(
    db: Session = Depends(get_db),
) -> SimilarityDistributionOut:
    """Return count of SimilarityReport records in each 10-percentage-point bucket.

    Validates: Requirements 19.5
    """
    return analytics_service.similarity_distribution(db)


@router.get(
    "/cases-over-time",
    response_model=CasesOverTimeOut,
    summary="Monthly IntegrityCase counts, optionally filtered by date range",
)
def get_cases_over_time(
    from_date: Annotated[date | None, Query(alias="from_date")] = None,
    to_date: Annotated[date | None, Query(alias="to_date")] = None,
    db: Session = Depends(get_db),
) -> CasesOverTimeOut:
    """Return monthly case counts.

    Raises HTTP 422 when ``from_date`` > ``to_date``.

    Validates: Requirements 19.2
    """
    return analytics_service.cases_over_time(db, from_date, to_date)


@router.get(
    "/outcomes-by-program",
    response_model=OutcomesByProgramOut,
    summary="Decision outcomes grouped by learner programme",
)
def get_outcomes_by_program(
    db: Session = Depends(get_db),
) -> OutcomesByProgramOut:
    """Return decision-outcome counts for each programme.

    Validates: Requirements 19.3
    """
    return analytics_service.outcomes_by_program(db)


@router.get(
    "/top-assessments",
    response_model=TopAssessmentsOut,
    summary="Top 10 assessments by linked IntegrityCase count",
)
def get_top_assessments(
    db: Session = Depends(get_db),
) -> TopAssessmentsOut:
    """Return up to 10 assessments ranked by case count, highest first.

    Validates: Requirements 19.4
    """
    return analytics_service.top_assessments(db)
