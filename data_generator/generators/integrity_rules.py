"""
Generator for IntegrityRule reference data.

Produces exactly 10 IntegrityRule rows covering the four-tier similarity
threshold ladder plus six sub-range variants.  The DataFrame columns match
the `IntegrityRule` table defined in database/schema.sql.
"""

import pandas as pd
from datetime import date

from data_generator.utils.id_formatter import fmt_rule


# The date from which all generated rules are effective.
_EFFECTIVE_FROM = date(2025, 1, 1)


def generate_integrity_rules(rng) -> pd.DataFrame:
    """Generate exactly 10 IntegrityRule rows.

    The ``rng`` parameter is accepted for API consistency with all other
    generator functions but is not used internally — the rules are fully
    deterministic static reference data.

    Returns
    -------
    pd.DataFrame
        Columns: rule_id, rule_name, min_similarity, max_similarity,
                 action_type, priority, effective_from, effective_to,
                 is_active
    """
    rows = [
        # ── Primary four-tier ladder ─────────────────────────────────────
        {
            "rule_id":        fmt_rule(1),
            "rule_name":      "Low Similarity",
            "min_similarity": 0.00,
            "max_similarity": 40.00,
            "action_type":    "NO_REVIEW",
            "priority":       1,
            "effective_from": _EFFECTIVE_FROM,
            "effective_to":   None,
            "is_active":      True,
        },
        {
            "rule_id":        fmt_rule(2),
            "rule_name":      "Moderate Similarity",
            "min_similarity": 41.00,
            "max_similarity": 70.00,
            "action_type":    "MONITOR",
            "priority":       2,
            "effective_from": _EFFECTIVE_FROM,
            "effective_to":   None,
            "is_active":      True,
        },
        {
            "rule_id":        fmt_rule(3),
            "rule_name":      "High Similarity",
            "min_similarity": 71.00,
            "max_similarity": 85.00,
            "action_type":    "REVIEW",
            "priority":       3,
            "effective_from": _EFFECTIVE_FROM,
            "effective_to":   None,
            "is_active":      True,
        },
        {
            "rule_id":        fmt_rule(4),
            "rule_name":      "Very High Similarity",
            "min_similarity": 86.00,
            "max_similarity": 100.00,
            "action_type":    "HIGH_PRIORITY_REVIEW",
            "priority":       4,
            "effective_from": _EFFECTIVE_FROM,
            "effective_to":   None,
            "is_active":      True,
        },
        # ── Sub-range variants (rules 5–10) ──────────────────────────────
        {
            "rule_id":        fmt_rule(5),
            "rule_name":      "Very Low Similarity",
            "min_similarity": 0.00,
            "max_similarity": 20.00,
            "action_type":    "NO_REVIEW",
            "priority":       5,
            "effective_from": _EFFECTIVE_FROM,
            "effective_to":   None,
            "is_active":      True,
        },
        {
            "rule_id":        fmt_rule(6),
            "rule_name":      "Low-Mid Similarity",
            "min_similarity": 21.00,
            "max_similarity": 40.00,
            "action_type":    "NO_REVIEW",
            "priority":       6,
            "effective_from": _EFFECTIVE_FROM,
            "effective_to":   None,
            "is_active":      True,
        },
        {
            "rule_id":        fmt_rule(7),
            "rule_name":      "Lower Moderate Similarity",
            "min_similarity": 41.00,
            "max_similarity": 55.00,
            "action_type":    "MONITOR",
            "priority":       7,
            "effective_from": _EFFECTIVE_FROM,
            "effective_to":   None,
            "is_active":      True,
        },
        {
            "rule_id":        fmt_rule(8),
            "rule_name":      "Upper Moderate Similarity",
            "min_similarity": 56.00,
            "max_similarity": 70.00,
            "action_type":    "MONITOR",
            "priority":       8,
            "effective_from": _EFFECTIVE_FROM,
            "effective_to":   None,
            "is_active":      True,
        },
        {
            "rule_id":        fmt_rule(9),
            "rule_name":      "Lower High Similarity",
            "min_similarity": 71.00,
            "max_similarity": 78.00,
            "action_type":    "REVIEW",
            "priority":       9,
            "effective_from": _EFFECTIVE_FROM,
            "effective_to":   None,
            "is_active":      True,
        },
        {
            "rule_id":        fmt_rule(10),
            "rule_name":      "Upper High Similarity",
            "min_similarity": 79.00,
            "max_similarity": 85.00,
            "action_type":    "REVIEW",
            "priority":       10,
            "effective_from": _EFFECTIVE_FROM,
            "effective_to":   None,
            "is_active":      True,
        },
    ]

    df = pd.DataFrame(rows, columns=[
        "rule_id",
        "rule_name",
        "min_similarity",
        "max_similarity",
        "action_type",
        "priority",
        "effective_from",
        "effective_to",
        "is_active",
    ])

    assert len(df) == 10, f"Expected 10 IntegrityRule rows, got {len(df)}"
    return df
