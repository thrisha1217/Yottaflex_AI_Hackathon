"""
backend/models/__init__.py

Exports all ORM models so they are registered with the Base metadata
and are importable from `backend.models`.
"""

from backend.models.learner import Learner
from backend.models.assessment import Assessment
from backend.models.integrity_rule import IntegrityRule
from backend.models.reviewer import Reviewer
from backend.models.submission import Submission
from backend.models.similarity_report import SimilarityReport
from backend.models.integrity_case import IntegrityCase
from backend.models.case_reviewer import CaseReviewer
from backend.models.evidence_item import EvidenceItem
from backend.models.decision import Decision
from backend.models.decision_evidence import DecisionEvidence
from backend.models.appeal import Appeal
from backend.models.appeal_review import AppealReview
from backend.models.case_event import CaseEvent
from backend.models.audit_log import AuditLog

__all__ = [
    "Learner",
    "Assessment",
    "IntegrityRule",
    "Reviewer",
    "Submission",
    "SimilarityReport",
    "IntegrityCase",
    "CaseReviewer",
    "EvidenceItem",
    "Decision",
    "DecisionEvidence",
    "Appeal",
    "AppealReview",
    "CaseEvent",
    "AuditLog",
]
