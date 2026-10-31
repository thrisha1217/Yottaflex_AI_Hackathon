"""
Generator for Decision data.

Produces exactly 300 Decision rows, one per IntegrityCase.

All columns match the ``Decision`` table defined in ``database/schema.sql``.

Columns produced
----------------
decision_id          – sequential INT starting at 1 (matches AUTO_INCREMENT PK)
case_id              – FK into IntegrityCase; one decision per case
reviewer_id          – sampled from active reviewers in reviewers_df
previous_decision_id – always None (API handles revisions via new rows)
decision_outcome     – distributed across NO_VIOLATION, VIOLATION, INCONCLUSIVE
rationale            – faker.paragraph()
decided_at           – 5–25 days after the corresponding case's opened_at
is_final             – always True
"""

import random
from datetime import datetime, timedelta

import pandas as pd

from data_generator.config import TARGET_DECISIONS

# ------------------------------------------------------------------ #
# Constants                                                            #
# ------------------------------------------------------------------ #

# Three outcome values and their approximate weight distribution.
# Weights sum to 300 decisions:
#   NO_VIOLATION  ~45%  → 135
#   VIOLATION     ~35%  → 105
#   INCONCLUSIVE  ~20%  →  60
_OUTCOME_VALUES = ["NO_VIOLATION", "VIOLATION", "INCONCLUSIVE"]
_OUTCOME_WEIGHTS = [135, 105, 60]

# Days after opened_at that a decision is made (5–25 inclusive).
_MIN_DECISION_DELTA_DAYS = 5
_MAX_DECISION_DELTA_DAYS = 25


# ------------------------------------------------------------------ #
# Public API                                                           #
# ------------------------------------------------------------------ #


def generate_decisions(
    rng: random.Random,
    faker,
    cases_df: pd.DataFrame,
    reviewers_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate exactly 300 Decision rows, one per IntegrityCase.

    Parameters
    ----------
    rng:
        ``random.Random`` instance seeded externally.  *All* randomness
        flows through this object.
    faker:
        ``Faker`` instance seeded externally — used for ``rationale`` text.
    cases_df:
        DataFrame produced by ``generate_integrity_cases()``; must
        contain columns ``case_id`` and ``opened_at``.
    reviewers_df:
        DataFrame produced by ``generate_reviewers()``; must contain
        columns ``reviewer_id`` and ``status``.

    Returns
    -------
    pd.DataFrame
        Columns: decision_id, case_id, reviewer_id, previous_decision_id,
                 decision_outcome, rationale, decided_at, is_final
    """
    # ----------------------------------------------------------------
    # 1. Validate inputs
    # ----------------------------------------------------------------
    if len(cases_df) != TARGET_DECISIONS:
        raise ValueError(
            f"Expected exactly {TARGET_DECISIONS} IntegrityCase rows, "
            f"got {len(cases_df)}."
        )

    # ----------------------------------------------------------------
    # 2. Build the pool of active reviewers
    # ----------------------------------------------------------------
    active_reviewers_df = reviewers_df[reviewers_df["status"] == "ACTIVE"]

    if len(active_reviewers_df) == 0:
        raise ValueError("No active reviewers available to assign decisions.")

    active_reviewer_ids: list[str] = active_reviewers_df["reviewer_id"].tolist()

    # ----------------------------------------------------------------
    # 3. Pre-generate outcomes in bulk via rng.choices()
    # ----------------------------------------------------------------
    outcomes = rng.choices(_OUTCOME_VALUES, weights=_OUTCOME_WEIGHTS, k=TARGET_DECISIONS)

    # ----------------------------------------------------------------
    # 4. Build rows — iterate over cases in order
    # ----------------------------------------------------------------
    rows = []
    for n, (_, case_row) in enumerate(cases_df.iterrows()):
        decision_id = n + 1  # sequential INT starting at 1

        case_id = case_row["case_id"]

        opened_at: datetime = case_row["opened_at"]
        if isinstance(opened_at, pd.Timestamp):
            opened_at = opened_at.to_pydatetime()

        # decided_at is 5–25 days after opened_at
        delta_days = rng.randint(_MIN_DECISION_DELTA_DAYS, _MAX_DECISION_DELTA_DAYS)
        decided_at = opened_at + timedelta(days=delta_days)

        # reviewer_id sampled from active reviewers
        reviewer_id = rng.choice(active_reviewer_ids)

        decision_outcome = outcomes[n]

        rationale = faker.paragraph()

        rows.append({
            "decision_id":          decision_id,
            "case_id":              case_id,
            "reviewer_id":          reviewer_id,
            "previous_decision_id": None,
            "decision_outcome":     decision_outcome,
            "rationale":            rationale,
            "decided_at":           decided_at,
            "is_final":             True,
        })

    # ----------------------------------------------------------------
    # 5. Assemble DataFrame
    # ----------------------------------------------------------------
    df = pd.DataFrame(rows, columns=[
        "decision_id",
        "case_id",
        "reviewer_id",
        "previous_decision_id",
        "decision_outcome",
        "rationale",
        "decided_at",
        "is_final",
    ])

    # ----------------------------------------------------------------
    # 6. Sanity assertions
    # ----------------------------------------------------------------
    assert len(df) == TARGET_DECISIONS, \
        f"Expected {TARGET_DECISIONS} Decision rows, got {len(df)}"

    assert df["case_id"].is_unique, \
        "case_id values must be unique (one decision per case)"

    valid_outcomes = set(_OUTCOME_VALUES)
    assert df["decision_outcome"].isin(valid_outcomes).all(), \
        "All decision_outcome values must be valid enum members"

    assert df["is_final"].all(), \
        "is_final must be True for all rows"

    assert df["previous_decision_id"].isna().all(), \
        "previous_decision_id must be None for all rows (API handles revisions)"

    # decided_at must be strictly after opened_at for every row
    merged = df.merge(
        cases_df[["case_id", "opened_at"]],
        on="case_id",
        how="left",
    )
    decided_arr = pd.to_datetime(merged["decided_at"])
    opened_arr  = pd.to_datetime(merged["opened_at"])
    assert (decided_arr > opened_arr).all(), \
        "decided_at must be strictly after the corresponding case's opened_at"

    # reviewer_id must reference an active reviewer
    active_reviewer_set = set(active_reviewer_ids)
    assert df["reviewer_id"].isin(active_reviewer_set).all(), \
        "All reviewer_id values must reference active reviewers"

    return df
