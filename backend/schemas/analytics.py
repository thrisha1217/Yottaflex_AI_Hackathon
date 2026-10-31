"""
backend/schemas/analytics.py

Pydantic v2 schemas for the Analytics Engine aggregate-metrics endpoints
(Requirement 19).

    - SummaryOut                  (GET /analytics/summary)
    - MonthlyCaseCount            (nested item for cases-over-time)
    - CasesOverTimeOut            (GET /analytics/cases-over-time)
    - ProgramOutcomes             (nested item for outcomes-by-program)
    - OutcomesByProgramOut        (GET /analytics/outcomes-by-program)
    - AssessmentCaseCount         (nested item for top-assessments)
    - TopAssessmentsOut           (GET /analytics/top-assessments)
    - ScoreBucket                 (nested item for similarity-distribution)
    - SimilarityDistributionOut    (GET /analytics/similarity-distribution)

Validates: Requirements 19.1–19.5
"""

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Nested data items
#
# These are plain data containers produced by the analytics service layer
# (aggregate queries), so they do not need ``from_attributes`` — they are
# always constructed from dict results, not ORM objects.
# ---------------------------------------------------------------------------


class MonthlyCaseCount(BaseModel):
    """A single month/count pair for the cases-over-time chart.

    ``month`` is an ISO-8601 year-month string (e.g. ``"2026-01"``).
    """

    month: str
    count: int


class ProgramOutcomes(BaseModel):
    """Decision-outcome counts for a single programme.

    Field names match the ``decision_outcome`` enum values so the Dashboard
    can map them directly to stacked-bar segments.
    """

    program: str
    NO_VIOLATION: int
    VIOLATION: int
    INCONCLUSIVE: int


class AssessmentCaseCount(BaseModel):
    """An assessment ranked by linked IntegrityCase count."""

    assessment_id: str
    title: str
    case_count: int


class ScoreBucket(BaseModel):
    """A single 10-percentage-point similarity-score bucket.

    ``bucket`` is a label such as ``"0-10"`` or ``"91-100"``.
    """

    bucket: str
    count: int


# ---------------------------------------------------------------------------
# Response envelopes
# ---------------------------------------------------------------------------


class SummaryOut(BaseModel):
    """High-level aggregate counts returned by ``GET /analytics/summary``.

    Validates: Requirements 19.1
    """

    model_config = ConfigDict(from_attributes=True)

    total_submissions: int
    flagged_submissions: int
    total_cases: int
    total_decisions: int
    total_appeals: int


class CasesOverTimeOut(BaseModel):
    """Monthly case counts returned by ``GET /analytics/cases-over-time``.

    Validates: Requirements 19.2
    """

    data: list[MonthlyCaseCount]


class OutcomesByProgramOut(BaseModel):
    """Decision outcomes grouped by programme.

    Returned by ``GET /analytics/outcomes-by-program``.

    Validates: Requirements 19.3
    """

    data: list[ProgramOutcomes]


class TopAssessmentsOut(BaseModel):
    """Top assessments by IntegrityCase count.

    Returned by ``GET /analytics/top-assessments``.

    Validates: Requirements 19.4
    """

    data: list[AssessmentCaseCount]


class SimilarityDistributionOut(BaseModel):
    """Counts of SimilarityReport records per score bucket.

    Returned by ``GET /analytics/similarity-distribution``.

    Validates: Requirements 19.5
    """

    data: list[ScoreBucket]
