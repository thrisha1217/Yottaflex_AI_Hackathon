"""backend/schemas package — Pydantic request/response schemas."""

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
from backend.schemas.appeals import (
    AppealCreate,
    AppealOut,
    AppealReviewCreate,
    AppealReviewOut,
)
from backend.schemas.audit_log import (
    AuditLogOut,
    PaginatedAuditLog,
)
from backend.schemas.audit_reports import (
    AppealsWithoutReviewOut,
    ConflictReassignmentOut,
    EvidenceItemSummary,
    PostDecisionEvidenceOut,
)
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
from backend.schemas.decisions import (
    DecisionCreate,
    DecisionOut,
)
from backend.schemas.evidence import (
    EvidenceItemCreate,
    EvidenceItemOut,
)
from backend.schemas.reviewers import (
    CaseReviewerCreate,
    CaseReviewerOut,
    ConflictUpdate,
    PaginatedReviewers,
    ReviewerOut,
)
from backend.schemas.submissions import (
    PaginatedSubmissions,
    RuleSummary,
    SimilarityReportDetail,
    SimilarityReportSummary,
    SubmissionDetail,
    SubmissionSummary,
)

__all__ = [
    # Analytics
    "AssessmentCaseCount",
    "CasesOverTimeOut",
    "MonthlyCaseCount",
    "OutcomesByProgramOut",
    "ProgramOutcomes",
    "ScoreBucket",
    "SimilarityDistributionOut",
    "SummaryOut",
    "TopAssessmentsOut",
    # Appeals
    "AppealCreate",
    "AppealOut",
    "AppealReviewCreate",
    "AppealReviewOut",
    # Audit log
    "AuditLogOut",
    "PaginatedAuditLog",
    # Audit reports
    "AppealsWithoutReviewOut",
    "ConflictReassignmentOut",
    "EvidenceItemSummary",
    "PostDecisionEvidenceOut",
    # Cases
    "CaseDetail",
    "CaseEventOut",
    "CaseReviewerSummary",
    "CaseStatus",
    "CaseStatusUpdate",
    "CaseSummary",
    "DecisionSummary",
    "PaginatedCases",
    "Priority",
    # Decisions
    "DecisionCreate",
    "DecisionOut",
    # Evidence
    "EvidenceItemCreate",
    "EvidenceItemOut",
    # Reviewers
    "CaseReviewerCreate",
    "CaseReviewerOut",
    "ConflictUpdate",
    "PaginatedReviewers",
    "ReviewerOut",
    # Submissions
    "PaginatedSubmissions",
    "RuleSummary",
    "SimilarityReportDetail",
    "SimilarityReportSummary",
    "SubmissionDetail",
    "SubmissionSummary",
]
