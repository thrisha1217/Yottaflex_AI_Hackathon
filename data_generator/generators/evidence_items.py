"""
Generator for EvidenceItem data.

Produces approximately 900 EvidenceItem rows, targeting ~3 per case
(300 cases × 3 = 900).

All columns match the ``EvidenceItem`` table defined in
``database/schema.sql``.

Columns produced
----------------
evidence_id        – formatted via fmt_evidence(case_id, n) → EVD-INT-2026-000001-001 … EVD-INT-2026-000300-003
case_id            – FK into IntegrityCase; each case receives ~3 evidence rows
evidence_type      – distributed across all six enum values:
                       SIMILARITY_MATCH, QUOTATION, TEMPLATE,
                       STUDENT_EXPLANATION, DOCUMENT, OTHER
description        – faker.sentence()
evidence_reference – NULL for generated rows (populated by the API layer)
added_by_role      – distributed across REVIEWER, ACADEMIC_ADMIN, INSTRUCTOR
                     (LEARNER and SYSTEM roles are handled at the API layer)
added_by_ref       – NULL for generated rows
added_at           – 1–10 days after the corresponding case's opened_at
is_material        – TRUE for all generated rows (post-decision evidence
                     handled by the API layer per schema design note)
"""

import random
from datetime import timedelta

import pandas as pd

from data_generator.config import TARGET_EVIDENCE
from data_generator.utils.id_formatter import fmt_evidence

# ------------------------------------------------------------------ #
# Constants                                                            #
# ------------------------------------------------------------------ #

# Six evidence_type enum values with roughly equal distribution.
_EVIDENCE_TYPE_VALUES = [
    "SIMILARITY_MATCH",
    "QUOTATION",
    "TEMPLATE",
    "STUDENT_EXPLANATION",
    "DOCUMENT",
    "OTHER",
]
_EVIDENCE_TYPE_WEIGHTS = [220, 150, 100, 180, 150, 100]  # sum = 900

# added_by_role values available for generator rows (API layer handles
# LEARNER and SYSTEM roles at runtime).
_ADDED_BY_ROLE_VALUES = ["REVIEWER", "ACADEMIC_ADMIN", "INSTRUCTOR"]
_ADDED_BY_ROLE_WEIGHTS = [400, 300, 200]  # sum = 900

# Days after case.opened_at that evidence is added (1–10 inclusive).
_MIN_ADDED_DELTA_DAYS = 1
_MAX_ADDED_DELTA_DAYS = 10

# Tolerance band for the ~900 row count assertion.
_ROW_COUNT_LOW  = 870
_ROW_COUNT_HIGH = 930


# ------------------------------------------------------------------ #
# Public API                                                           #
# ------------------------------------------------------------------ #


def generate_evidence_items(
    rng: random.Random,
    faker,
    cases_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate approximately 900 EvidenceItem rows (~3 per case).

    Parameters
    ----------
    rng:
        ``random.Random`` instance seeded externally.  *All* randomness
        flows through this object (including faker, which is seeded
        once before the generator chain starts).
    faker:
        ``Faker`` instance used to produce ``description`` text.
    cases_df:
        DataFrame produced by ``generate_integrity_cases()``; must
        contain columns ``case_id`` and ``opened_at``.

    Returns
    -------
    pd.DataFrame
        Columns: evidence_id, case_id, evidence_type, description,
                 evidence_reference, added_by_role, added_by_ref,
                 added_at, is_material
    """
    case_ids = cases_df["case_id"].tolist()
    num_cases = len(case_ids)

    # ----------------------------------------------------------------
    # 1. Determine how many evidence items each case receives so the
    #    total is exactly TARGET_EVIDENCE.
    #    Base = 3 per case; distribute the remainder randomly.
    # ----------------------------------------------------------------
    base_per_case = TARGET_EVIDENCE // num_cases          # = 3
    remainder     = TARGET_EVIDENCE - base_per_case * num_cases  # = 0 for 300 cases

    counts = [base_per_case] * num_cases

    # Distribute any leftover rows across randomly chosen cases.
    if remainder > 0:
        extra_indices = rng.sample(range(num_cases), remainder)
        for idx in extra_indices:
            counts[idx] += 1

    total_rows = sum(counts)  # should equal TARGET_EVIDENCE

    # ----------------------------------------------------------------
    # 2. Pre-generate all categorical values in bulk via rng.choices()
    #    so all randomness flows through the shared rng.
    # ----------------------------------------------------------------
    evidence_types  = rng.choices(_EVIDENCE_TYPE_VALUES,  weights=_EVIDENCE_TYPE_WEIGHTS,  k=total_rows)
    added_by_roles  = rng.choices(_ADDED_BY_ROLE_VALUES,  weights=_ADDED_BY_ROLE_WEIGHTS,  k=total_rows)
    delta_days_list = [
        rng.randint(_MIN_ADDED_DELTA_DAYS, _MAX_ADDED_DELTA_DAYS)
        for _ in range(total_rows)
    ]

    # ----------------------------------------------------------------
    # 3. Build a lookup: case_id → opened_at (as Python datetime)
    # ----------------------------------------------------------------
    opened_at_map: dict = {}
    for _, row in cases_df.iterrows():
        opened_at = row["opened_at"]
        if hasattr(opened_at, "to_pydatetime"):
            opened_at = opened_at.to_pydatetime()
        opened_at_map[row["case_id"]] = opened_at

    # ----------------------------------------------------------------
    # 4. Build rows
    # ----------------------------------------------------------------
    rows = []
    global_counter = 0  # still needed for bulk pre-generated values

    for case_idx, case_id in enumerate(case_ids):
        case_opened_at = opened_at_map[case_id]
        n_items = counts[case_idx]

        for item_no in range(1, n_items + 1):
            global_counter += 1
            # Per-case numbering: EVD-INT-2026-000001-001
            evidence_id = fmt_evidence(case_id, item_no)

            evidence_type = evidence_types[global_counter - 1]
            added_by_role = added_by_roles[global_counter - 1]
            delta_days    = delta_days_list[global_counter - 1]
            added_at      = case_opened_at + timedelta(days=delta_days)
            description   = faker.sentence()

            rows.append({
                "evidence_id":        evidence_id,
                "case_id":            case_id,
                "evidence_type":      evidence_type,
                "description":        description,
                "evidence_reference": None,
                "added_by_role":      added_by_role,
                "added_by_ref":       None,
                "added_at":           added_at,
                "is_material":        True,
            })

    # ----------------------------------------------------------------
    # 5. Assemble DataFrame
    # ----------------------------------------------------------------
    df = pd.DataFrame(rows, columns=[
        "evidence_id",
        "case_id",
        "evidence_type",
        "description",
        "evidence_reference",
        "added_by_role",
        "added_by_ref",
        "added_at",
        "is_material",
    ])

    # ----------------------------------------------------------------
    # 6. Sanity assertions
    # ----------------------------------------------------------------
    assert _ROW_COUNT_LOW <= len(df) <= _ROW_COUNT_HIGH, (
        f"Expected between {_ROW_COUNT_LOW} and {_ROW_COUNT_HIGH} EvidenceItem rows, "
        f"got {len(df)}"
    )

    case_id_set = set(cases_df["case_id"])
    assert df["case_id"].isin(case_id_set).all(), (
        "Every case_id in EvidenceItem must reference an existing IntegrityCase"
    )

    assert df["is_material"].all(), (
        "All is_material values must be True for generator-produced rows"
    )

    opened_at_series = cases_df.set_index("case_id")["opened_at"]
    merged = df.merge(
        cases_df[["case_id", "opened_at"]],
        on="case_id",
        how="left",
    )
    added_arr  = pd.to_datetime(merged["added_at"])
    opened_arr = pd.to_datetime(merged["opened_at"])
    assert (added_arr > opened_arr).all(), (
        "added_at must be strictly after the corresponding case's opened_at"
    )

    valid_types = set(_EVIDENCE_TYPE_VALUES)
    assert df["evidence_type"].isin(valid_types).all(), (
        "All evidence_type values must be valid enum members"
    )

    valid_roles = {"REVIEWER", "ACADEMIC_ADMIN", "INSTRUCTOR", "LEARNER", "SYSTEM"}
    assert df["added_by_role"].isin(valid_roles).all(), (
        "All added_by_role values must be valid enum members"
    )

    return df
