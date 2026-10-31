"""
Generator for Appeal data.

Produces approximately 90 Appeal rows, one per sampled IntegrityCase that
has a corresponding Decision record.

All columns match the ``Appeal`` table defined in ``database/schema.sql``.

Columns produced
----------------
appeal_id     – formatted via fmt_appeal(n) → APL-000001 through APL-000090
case_id       – FK into IntegrityCase; sampled from cases that have a Decision row
learner_id    – FK into Learner; sampled from learners_df
appeal_no     – always 1 (first appeal per case; unique constraint: (case_id, appeal_no))
reason        – faker.sentence() — grounds for the appeal
submitted_at  – 5–30 days after the corresponding case's decided_at (if available),
                else 5–30 days after the case's opened_at
appeal_status – distributed across all five enum values:
                  SUBMITTED, UNDER_REVIEW, UPHELD, OVERTURNED, REMANDED
resolved_at   – set (a few days after submitted_at) for UPHELD/OVERTURNED;
                NULL for SUBMITTED, UNDER_REVIEW, REMANDED
"""

import random
from datetime import datetime, timedelta

import pandas as pd

from data_generator.config import TARGET_APPEALS
from data_generator.utils.id_formatter import fmt_appeal

# ------------------------------------------------------------------ #
# Constants                                                            #
# ------------------------------------------------------------------ #

# Five appeal_status values and their approximate weight distribution.
# Weights sum to ~90 appeals:
#   SUBMITTED      ~22%  → 20
#   UNDER_REVIEW   ~22%  → 20
#   UPHELD         ~17%  → 15
#   OVERTURNED     ~17%  → 15
#   REMANDED       ~22%  → 20
_STATUS_VALUES = [
    "SUBMITTED",
    "UNDER_REVIEW",
    "UPHELD",
    "OVERTURNED",
    "REMANDED",
]
_STATUS_WEIGHTS = [20, 20, 15, 15, 20]

# Statuses that have a non-null resolved_at
_RESOLVED_STATUSES = {"UPHELD", "OVERTURNED"}

# Days after decided_at (or opened_at) that an appeal is submitted (5–30 inclusive).
_MIN_SUBMIT_DELTA_DAYS = 5
_MAX_SUBMIT_DELTA_DAYS = 30

# Days after submitted_at that a resolved appeal is resolved (2–7 inclusive).
_MIN_RESOLVE_DELTA_DAYS = 2
_MAX_RESOLVE_DELTA_DAYS = 7


# ------------------------------------------------------------------ #
# Public API                                                           #
# ------------------------------------------------------------------ #


def generate_appeals(
    rng: random.Random,
    faker,
    cases_df: pd.DataFrame,
    decisions_df: pd.DataFrame,
    learners_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate approximately 90 Appeal rows.

    Parameters
    ----------
    rng:
        ``random.Random`` instance seeded externally.  *All* randomness
        flows through this object.
    faker:
        ``Faker`` instance seeded externally — used for ``reason`` text.
    cases_df:
        DataFrame produced by ``generate_integrity_cases()``; must
        contain columns ``case_id`` and ``opened_at``.
    decisions_df:
        DataFrame produced by ``generate_decisions()``; must contain
        columns ``case_id`` and ``decided_at``.
    learners_df:
        DataFrame produced by ``generate_learners()``; must contain
        column ``learner_id``.

    Returns
    -------
    pd.DataFrame
        Columns: appeal_id, case_id, learner_id, appeal_no, reason,
                 submitted_at, appeal_status, resolved_at
    """
    # ----------------------------------------------------------------
    # 1. Build the pool of eligible cases: only those with a Decision row
    # ----------------------------------------------------------------
    decided_case_ids = set(decisions_df["case_id"].tolist())

    eligible_cases_df = cases_df[cases_df["case_id"].isin(decided_case_ids)].copy()
    eligible_cases_df = eligible_cases_df.reset_index(drop=True)

    if len(eligible_cases_df) < TARGET_APPEALS:
        raise ValueError(
            f"Not enough cases with decisions to generate {TARGET_APPEALS} appeals: "
            f"only {len(eligible_cases_df)} eligible cases available."
        )

    # ----------------------------------------------------------------
    # 2. Sample TARGET_APPEALS cases WITHOUT replacement
    # ----------------------------------------------------------------
    sampled_indices = rng.sample(range(len(eligible_cases_df)), TARGET_APPEALS)
    sampled_cases_df = eligible_cases_df.iloc[sampled_indices].reset_index(drop=True)

    # ----------------------------------------------------------------
    # 3. Build a lookup: case_id → decided_at from decisions_df
    # ----------------------------------------------------------------
    decided_at_lookup: dict[str, datetime] = {}
    for _, row in decisions_df.iterrows():
        cid = row["case_id"]
        da = row["decided_at"]
        if isinstance(da, pd.Timestamp):
            da = da.to_pydatetime()
        decided_at_lookup[cid] = da

    # ----------------------------------------------------------------
    # 4. Pre-generate appeal statuses in bulk
    # ----------------------------------------------------------------
    statuses = rng.choices(_STATUS_VALUES, weights=_STATUS_WEIGHTS, k=TARGET_APPEALS)

    # ----------------------------------------------------------------
    # 5. Build the list of learner IDs for sampling
    # ----------------------------------------------------------------
    learner_ids: list[str] = learners_df["learner_id"].tolist()

    # ----------------------------------------------------------------
    # 6. Build rows
    # ----------------------------------------------------------------
    rows = []
    for n in range(TARGET_APPEALS):
        appeal_id = fmt_appeal(n + 1)  # APL-000001 …

        case_row = sampled_cases_df.iloc[n]
        case_id = case_row["case_id"]

        # opened_at as fallback base
        opened_at: datetime = case_row["opened_at"]
        if isinstance(opened_at, pd.Timestamp):
            opened_at = opened_at.to_pydatetime()

        # Use decided_at if available, otherwise fall back to opened_at
        base_dt = decided_at_lookup.get(case_id, opened_at)

        # submitted_at: 5–30 days after base_dt
        submit_delta = rng.randint(_MIN_SUBMIT_DELTA_DAYS, _MAX_SUBMIT_DELTA_DAYS)
        submitted_at = base_dt + timedelta(days=submit_delta)

        # learner_id sampled from learners_df
        learner_id = rng.choice(learner_ids)

        appeal_status = statuses[n]

        # resolved_at: set only for UPHELD and OVERTURNED
        if appeal_status in _RESOLVED_STATUSES:
            resolve_delta = rng.randint(_MIN_RESOLVE_DELTA_DAYS, _MAX_RESOLVE_DELTA_DAYS)
            resolved_at = submitted_at + timedelta(days=resolve_delta)
        else:
            resolved_at = None

        reason = faker.sentence()

        rows.append({
            "appeal_id":     appeal_id,
            "case_id":       case_id,
            "learner_id":    learner_id,
            "appeal_no":     1,
            "reason":        reason,
            "submitted_at":  submitted_at,
            "appeal_status": appeal_status,
            "resolved_at":   resolved_at,
        })

    # ----------------------------------------------------------------
    # 7. Assemble DataFrame
    # ----------------------------------------------------------------
    df = pd.DataFrame(rows, columns=[
        "appeal_id",
        "case_id",
        "learner_id",
        "appeal_no",
        "reason",
        "submitted_at",
        "appeal_status",
        "resolved_at",
    ])

    # ----------------------------------------------------------------
    # 8. Sanity assertions
    # ----------------------------------------------------------------
    assert 80 <= len(df) <= 100, \
        f"Expected approximately 90 Appeal rows (80–100), got {len(df)}"

    assert df["appeal_id"].is_unique, \
        "appeal_id values must be unique"

    # All case_id values must reference cases that have a Decision row
    assert df["case_id"].isin(decided_case_ids).all(), \
        "Every case_id in Appeal must reference a case with a Decision row"

    valid_statuses = set(_STATUS_VALUES)
    assert df["appeal_status"].isin(valid_statuses).all(), \
        "All appeal_status values must be valid enum members"

    assert set(df["appeal_status"]) == valid_statuses, (
        f"All five appeal_status values must appear; "
        f"missing: {valid_statuses - set(df['appeal_status'])}"
    )

    # resolved_at must be non-null for UPHELD/OVERTURNED, null for others
    resolved_mask = df["appeal_status"].isin(_RESOLVED_STATUSES)
    assert df.loc[resolved_mask, "resolved_at"].notna().all(), \
        "resolved_at must be non-NULL for UPHELD and OVERTURNED appeals"
    assert df.loc[~resolved_mask, "resolved_at"].isna().all(), \
        "resolved_at must be NULL for SUBMITTED, UNDER_REVIEW, and REMANDED appeals"

    # resolved_at >= submitted_at for resolved rows
    if resolved_mask.any():
        submitted_arr = pd.to_datetime(df.loc[resolved_mask, "submitted_at"])
        resolved_arr = pd.to_datetime(df.loc[resolved_mask, "resolved_at"])
        assert (resolved_arr >= submitted_arr).all(), \
            "resolved_at must be >= submitted_at for every resolved appeal"

    # submitted_at must be after the corresponding case's opened_at
    merged = df.merge(
        cases_df[["case_id", "opened_at"]],
        on="case_id",
        how="left",
    )
    submitted_arr = pd.to_datetime(merged["submitted_at"])
    opened_arr = pd.to_datetime(merged["opened_at"])
    assert (submitted_arr > opened_arr).all(), \
        "submitted_at must be strictly after the corresponding case's opened_at"

    # appeal_no must be 1 for all rows
    assert (df["appeal_no"] == 1).all(), \
        "appeal_no must be 1 for all rows (first appeal per case)"

    # learner_id must reference a valid learner
    valid_learner_ids = set(learners_df["learner_id"].tolist())
    assert df["learner_id"].isin(valid_learner_ids).all(), \
        "All learner_id values must reference valid learners"

    return df
