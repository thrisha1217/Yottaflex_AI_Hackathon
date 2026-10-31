"""
Generator for IntegrityCase data.

Produces exactly 300 IntegrityCase rows, one per sampled flagged
SimilarityReport (``review_required = TRUE``).

All columns match the ``IntegrityCase`` table defined in
``database/schema.sql``.

Columns produced
----------------
case_id       – formatted via fmt_case(2026, n) → INT-2026-000001 … INT-2026-000300
report_id     – unique FK into SimilarityReport; sampled WITHOUT replacement
                from the pool of flagged reports
case_status   – distributed across all six enum values:
                  OPEN, UNDER_REVIEW, AWAITING_INFORMATION,
                  DECIDED, APPEAL_PENDING, CLOSED
priority      – distributed across LOW, MEDIUM, HIGH
opened_at     – 1–5 days after the corresponding report's generated_at
closed_at     – set (a few days after opened_at) for CLOSED cases; NULL otherwise
"""

import random
from datetime import datetime, timedelta

import pandas as pd

from data_generator.config import TARGET_CASES
from data_generator.utils.id_formatter import fmt_case

# ------------------------------------------------------------------ #
# Constants                                                            #
# ------------------------------------------------------------------ #

_YEAR = 2026

# Six case_status values and their approximate weight distribution.
# Weights sum to 300 cases:
#   OPEN                 ~15%  → 45
#   UNDER_REVIEW         ~20%  → 60
#   AWAITING_INFORMATION ~10%  → 30
#   DECIDED              ~25%  → 75
#   APPEAL_PENDING       ~10%  → 30
#   CLOSED               ~20%  → 60
_STATUS_VALUES = [
    "OPEN",
    "UNDER_REVIEW",
    "AWAITING_INFORMATION",
    "DECIDED",
    "APPEAL_PENDING",
    "CLOSED",
]
_STATUS_WEIGHTS = [45, 60, 30, 75, 30, 60]

# Three priority values with roughly natural distribution.
_PRIORITY_VALUES  = ["LOW", "MEDIUM", "HIGH"]
_PRIORITY_WEIGHTS = [60, 150, 90]   # ~20%, ~50%, ~30%

# Days after generated_at that a case is opened (1–5 inclusive).
_MIN_OPEN_DELTA_DAYS = 1
_MAX_OPEN_DELTA_DAYS = 5

# Days after opened_at that a CLOSED case is closed (3–14 inclusive).
_MIN_CLOSE_DELTA_DAYS = 3
_MAX_CLOSE_DELTA_DAYS = 14


# ------------------------------------------------------------------ #
# Public API                                                           #
# ------------------------------------------------------------------ #


def generate_integrity_cases(
    rng: random.Random,
    reports_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate exactly 300 IntegrityCase rows.

    Parameters
    ----------
    rng:
        ``random.Random`` instance seeded externally.  *All* randomness
        flows through this object.
    reports_df:
        DataFrame produced by ``generate_similarity_reports()``; must
        contain columns ``report_id``, ``review_required``, and
        ``generated_at``.

    Returns
    -------
    pd.DataFrame
        Columns: case_id, report_id, case_status, priority,
                 opened_at, closed_at
    """
    # ----------------------------------------------------------------
    # 1. Build the pool of eligible (flagged) reports
    # ----------------------------------------------------------------
    flagged_df = reports_df[reports_df["review_required"] == True].copy()

    if len(flagged_df) < TARGET_CASES:
        raise ValueError(
            f"Not enough flagged reports to generate {TARGET_CASES} cases: "
            f"only {len(flagged_df)} available."
        )

    # ----------------------------------------------------------------
    # 2. Sample TARGET_CASES report rows WITHOUT replacement
    #    rng.sample() ensures uniqueness (no duplicate report_id values)
    # ----------------------------------------------------------------
    sampled_indices = rng.sample(range(len(flagged_df)), TARGET_CASES)
    sampled_df = flagged_df.iloc[sampled_indices].reset_index(drop=True)

    # ----------------------------------------------------------------
    # 3. Pre-generate all status and priority values in bulk using
    #    rng.choices() so all randomness stays in the shared rng
    # ----------------------------------------------------------------
    statuses   = rng.choices(_STATUS_VALUES,   weights=_STATUS_WEIGHTS,   k=TARGET_CASES)
    priorities = rng.choices(_PRIORITY_VALUES, weights=_PRIORITY_WEIGHTS, k=TARGET_CASES)

    # ----------------------------------------------------------------
    # 4. Build rows
    # ----------------------------------------------------------------
    rows = []
    for n in range(TARGET_CASES):
        case_id    = fmt_case(_YEAR, n + 1)          # INT-2026-000001 …
        report_row = sampled_df.iloc[n]
        report_id  = report_row["report_id"]

        generated_at: datetime = report_row["generated_at"]
        if isinstance(generated_at, pd.Timestamp):
            generated_at = generated_at.to_pydatetime()

        # opened_at is 1–5 days after the report's generated_at
        open_delta = rng.randint(_MIN_OPEN_DELTA_DAYS, _MAX_OPEN_DELTA_DAYS)
        opened_at  = generated_at + timedelta(days=open_delta)

        case_status = statuses[n]
        priority    = priorities[n]

        # closed_at is set only for CLOSED cases
        if case_status == "CLOSED":
            close_delta = rng.randint(_MIN_CLOSE_DELTA_DAYS, _MAX_CLOSE_DELTA_DAYS)
            closed_at   = opened_at + timedelta(days=close_delta)
        else:
            closed_at = None

        rows.append({
            "case_id":     case_id,
            "report_id":   report_id,
            "case_status": case_status,
            "priority":    priority,
            "opened_at":   opened_at,
            "closed_at":   closed_at,
        })

    # ----------------------------------------------------------------
    # 5. Assemble DataFrame
    # ----------------------------------------------------------------
    df = pd.DataFrame(rows, columns=[
        "case_id",
        "report_id",
        "case_status",
        "priority",
        "opened_at",
        "closed_at",
    ])

    # ----------------------------------------------------------------
    # 6. Sanity assertions
    # ----------------------------------------------------------------
    assert len(df) == TARGET_CASES, \
        f"Expected {TARGET_CASES} IntegrityCase rows, got {len(df)}"

    assert df["case_id"].is_unique, \
        "case_id values must be unique"

    assert df["report_id"].is_unique, \
        "report_id values must be unique (one case per flagged report)"

    flagged_report_ids = set(flagged_df["report_id"])
    assert df["report_id"].isin(flagged_report_ids).all(), \
        "Every report_id must reference a flagged (review_required=TRUE) SimilarityReport"

    valid_statuses = set(_STATUS_VALUES)
    assert df["case_status"].isin(valid_statuses).all(), \
        "All case_status values must be valid enum members"

    assert set(df["case_status"]) == valid_statuses, \
        f"All six case_status values must appear; missing: {valid_statuses - set(df['case_status'])}"

    valid_priorities = set(_PRIORITY_VALUES)
    assert df["priority"].isin(valid_priorities).all(), \
        "All priority values must be valid enum members"

    # opened_at must be after generated_at for its corresponding report
    merged = df.merge(
        reports_df[["report_id", "generated_at"]],
        on="report_id",
        how="left",
    )
    # Normalise to datetime for comparison
    opened_arr    = pd.to_datetime(merged["opened_at"])
    generated_arr = pd.to_datetime(merged["generated_at"])
    assert (opened_arr > generated_arr).all(), \
        "opened_at must be strictly after the corresponding report's generated_at"

    # closed_at must be NULL for non-CLOSED cases and non-NULL for CLOSED
    closed_mask = df["case_status"] == "CLOSED"
    assert df.loc[closed_mask,  "closed_at"].notna().all(), \
        "closed_at must be non-NULL for CLOSED cases"
    assert df.loc[~closed_mask, "closed_at"].isna().all(), \
        "closed_at must be NULL for non-CLOSED cases"

    # closed_at >= opened_at for CLOSED cases
    if closed_mask.any():
        closed_opened  = pd.to_datetime(df.loc[closed_mask, "opened_at"])
        closed_closedat = pd.to_datetime(df.loc[closed_mask, "closed_at"])
        assert (closed_closedat >= closed_opened).all(), \
            "closed_at must be >= opened_at for every CLOSED case"

    return df
