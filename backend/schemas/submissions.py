"""
backend/schemas/submissions.py

Pydantic v2 response schemas for the Submission and SimilarityReport API
endpoints (Requirement 7). All schemas enable `from_attributes` so they can
be built directly from SQLAlchemy ORM instances via `model_validate`.

Validates: Requirements 7.1, 7.2, 7.3, 7.4
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RuleSummary(BaseModel):
    """
    Minimal IntegrityRule summary embedded inside SimilarityReportDetail.

    Only the fields relevant to interpreting a report are surfaced
    (rule_id, rule_name, action_type) — not the threshold bounds or
    effective dates, which are administrative.
    """

    model_config = ConfigDict(from_attributes=True)

    rule_id: str
    rule_name: str
    action_type: str


class SimilarityReportSummary(BaseModel):
    """
    Summary of a SimilarityReport, embedded in SubmissionDetail.

    This is the "lightweight" view used when a report is nested under a
    submission — enough to decide whether to drill into the full report.
    """

    model_config = ConfigDict(from_attributes=True)

    report_id: str
    submission_id: str
    similarity_score: float
    review_required: bool
    report_status: str
    generated_at: datetime


class SimilarityReportDetail(SimilarityReportSummary):
    """
    Full SimilarityReport record including the linked IntegrityRule details.

    Returned by `GET /similarity-reports/{report_id}` (Requirement 7.6).
    Extends the summary with the remaining report fields and the optional
    IntegrityRule summary.
    """

    report_no: int
    matched_source_count: int
    rule_id: Optional[str] = None
    rule: Optional[RuleSummary] = None


class SubmissionSummary(BaseModel):
    """
    Summary fields for a single submission list item (Requirement 7.1).

    `similarity_score` and `review_required` are derived from the linked
    SimilarityReport and are optional — a submission may not yet have a
    report attached. The service layer populates these from the
    `submission.report` relationship when building list responses.
    """

    model_config = ConfigDict(from_attributes=True)

    submission_id: str
    learner_id: str
    assessment_id: str
    attempt_no: int
    submitted_at: datetime
    status: str
    similarity_score: Optional[float] = None
    review_required: Optional[bool] = None


class SubmissionDetail(SubmissionSummary):
    """
    Full submission record with its linked SimilarityReport (Requirement 7.2).

    Adds the content fields (content_reference, content_hash) that are not
    needed in list views, plus the nested SimilarityReportSummary. The
    `report` relationship is one-to-one (uselist=False), so it is a single
    optional object.
    """

    content_reference: Optional[str] = None
    content_hash: Optional[str] = None
    report: Optional[SimilarityReportSummary] = None


class PaginatedSubmissions(BaseModel):
    """
    Pagination envelope for `GET /submissions` (Requirements 7.3, 7.4).

    `items` holds SubmissionSummary rows for the requested page. `total_count`
    is the total number of matching rows (before paging) so clients can render
    page controls. `len(items) <= page_size`.
    """

    items: list[SubmissionSummary]
    total_count: int
    page: int
    page_size: int
