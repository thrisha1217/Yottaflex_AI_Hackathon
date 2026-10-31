"""
ID formatting helpers for all entity types in the Academic Integrity system.

Each function takes one or more integer identifiers and returns the canonical
string ID used across CSV output and database records.
"""


def fmt_learner(n: int) -> str:
    """Format a learner ID. Example: fmt_learner(1) -> 'LRN-001'"""
    return f"LRN-{n:03d}"


def fmt_reviewer(n: int) -> str:
    """Format a reviewer ID. Example: fmt_reviewer(1) -> 'REV-001'"""
    return f"REV-{n:03d}"


def fmt_assessment(n: int) -> str:
    """Format an assessment ID. Example: fmt_assessment(1) -> 'ASM-001'"""
    return f"ASM-{n:03d}"


def fmt_rule(n: int) -> str:
    """Format an integrity rule ID. Example: fmt_rule(1) -> 'RULE-001'"""
    return f"RULE-{n:03d}"


def fmt_submission(year: int, n: int) -> str:
    """Format a submission ID. Example: fmt_submission(2026, 1) -> 'SUB-2026-000001'"""
    return f"SUB-{year}-{n:06d}"


def fmt_report(sub_id: str, n: int) -> str:
    """Format a similarity report ID. Example: fmt_report('SUB-2026-000001', 1) -> 'SIM-SUB-2026-000001-01'"""
    return f"SIM-{sub_id}-{n:02d}"


def fmt_case(year: int, n: int) -> str:
    """Format an integrity case ID. Example: fmt_case(2026, 1) -> 'INT-2026-000001'"""
    return f"INT-{year}-{n:06d}"


def fmt_evidence(case_id: str, n: int) -> str:
    """Format an evidence item ID using case-scoped numbering.
    
    Example: fmt_evidence('INT-2026-000001', 1) -> 'EVD-INT-2026-000001-001'
    
    Matches the brief convention: EVD-<case-id>-001
    """
    return f"EVD-{case_id}-{n:03d}"


def fmt_appeal(n: int) -> str:
    """Format an appeal ID. Example: fmt_appeal(1) -> 'APL-000001'"""
    return f"APL-{n:06d}"
