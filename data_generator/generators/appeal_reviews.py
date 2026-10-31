"""
Generator for AppealReview data.

Produces approximately 80 AppealReview rows.

Hard constraint
---------------
Every appeal with ``appeal_status IN ('UPHELD', 'OVERTURNED')`` must have
at least one AppealReview row where ``independence_verified = True``.

Independence constraint
-----------------------
The ``reviewer_id`` on each AppealReview row must differ from the PRIMARY
CaseReviewer assigned to the linked case.

All columns match the ``AppealReview`` table defined in
``database/schema.sql``.

Columns produced
----------------
review_id             – sequential integer starting at 1 (AUTO_INCREMENT PK)
appeal_id             – FK → Appeal
reviewer_id           – FK → Reviewer; must differ from PRIMARY case reviewer
outcome               – ENUM('UPHELD', 'OVERTURNED', 'REMANDED')
                        matches appeal_status for UPHELD/OVERTURNED rows;
                        distributed for other rows
rationale             – faker.sentence()
independence_verified – True for UPHELD/OVERTURNED rows; False for others
reviewed_at           – appeal's submitted_at + 3–14 days
"""

import random
from datetime import timedelta

import pandas as pd

from data_generator.config import TARGET_APPEAL_REVIEWS

# ------------------------------------------------------------------ #
# Constants                                                            #
# ------------------------------------------------------------------ #

# Appeal statuses that require a review row with independence_verified = True
_RESOLVED_STATUSES = {"UPHELD", "OVERTURNED"}

# Appeal statuses that can optionally fill remaining rows
_OPTIONAL_STATUSES = {"SUBMITTED", "UNDER_REVIEW", "REMANDED"}

# Valid outcome enum values
_VALID_OUTCOMES = {"UPHELD", "OVERTURNED", "REMANDED"}

# Outcome distribution weights for non-resolved appeals (SUBMITTED / UNDER_REVIEW / REMANDED)
_OPTIONAL_OUTCOME_VALUES = ["UPHELD", "OVERTURNED", "REMANDED"]
_OPTIONAL_OUTCOME_WEIGHTS = [2, 2, 6]  # skew toward REMANDED for pending appeals

# Days after submitted_at that the review is completed (3–14 inclusive)
_MIN_REVIEW_DELTA_DAYS = 3
_MAX_REVIEW_DELTA_DAYS = 14

# Tolerance band for the ~80 target
_MIN_ROWS = 70
_MAX_ROWS = 90


# ------------------------------------------------------------------ #
# Public API                                                           #
# ------------------------------------------------------------------ #


def generate_appeal_reviews(
    rng: random.Random,
    faker,
    appeals_df: pd.DataFrame,
    case_reviewers_df: pd.DataFrame,
    reviewers_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate approximately 80 AppealReview rows.

    Parameters
    ----------
    rng:
        ``random.Random`` instance seeded externally.  All randomness
        flows through this object.
    faker:
        ``Faker`` instance seeded externally — used for ``rationale`` text.
    appeals_df:
        DataFrame produced by ``generate_appeals()``; must contain columns
        ``appeal_id``, ``case_id``, ``appeal_status``, and ``submitted_at``.
    case_reviewers_df:
        DataFrame produced by ``generate_case_reviewers()``; must contain
        columns ``case_id``, ``reviewer_id``, and ``assignment_role``.
    reviewers_df:
        DataFrame produced by ``generate_reviewers()``; must contain
        column ``reviewer_id``.

    Returns
    -------
    pd.DataFrame
        Columns: review_id, appeal_id, reviewer_id, outcome, rationale,
                 independence_verified, reviewed_at
    """
    # ----------------------------------------------------------------
    # 1. Build lookup: case_id → primary_reviewer_id
    #    Use only rows where assignment_role = 'PRIMARY'.
    # ----------------------------------------------------------------
    primary_df = case_reviewers_df[case_reviewers_df["assignment_role"] == "PRIMARY"]
    primary_reviewer_map: dict[str, str] = dict(
        zip(primary_df["case_id"], primary_df["reviewer_id"])
    )

    # ----------------------------------------------------------------
    # 2. All available reviewer IDs (as a list for rng.choice)
    # ----------------------------------------------------------------
    all_reviewer_ids: list[str] = reviewers_df["reviewer_id"].tolist()

    # ----------------------------------------------------------------
    # 3. Helper: pick a reviewer_id ≠ primary reviewer for the case
    # ----------------------------------------------------------------
    def _pick_reviewer(case_id: str) -> str:
        primary = primary_reviewer_map.get(case_id)
        candidates = [r for r in all_reviewer_ids if r != primary]
        if not candidates:
            # Fallback: no other reviewer available (should not happen with 30 reviewers)
            return rng.choice(all_reviewer_ids)
        return rng.choice(candidates)

    # ----------------------------------------------------------------
    # 4. Helper: convert submitted_at to Python datetime
    # ----------------------------------------------------------------
    def _to_datetime(value):
        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime()
        return value

    # ----------------------------------------------------------------
    # 5. Split appeals by status
    # ----------------------------------------------------------------
    resolved_appeals = appeals_df[
        appeals_df["appeal_status"].isin(_RESOLVED_STATUSES)
    ].reset_index(drop=True)

    optional_appeals = appeals_df[
        appeals_df["appeal_status"].isin(_OPTIONAL_STATUSES)
    ].reset_index(drop=True)

    # ----------------------------------------------------------------
    # 6. Phase A — Mandatory rows for UPHELD/OVERTURNED appeals
    # ----------------------------------------------------------------
    rows: list[dict] = []

    for _, appeal_row in resolved_appeals.iterrows():
        appeal_id = appeal_row["appeal_id"]
        case_id = appeal_row["case_id"]
        submitted_at = _to_datetime(appeal_row["submitted_at"])
        appeal_status = appeal_row["appeal_status"]

        reviewer_id = _pick_reviewer(case_id)

        review_delta = rng.randint(_MIN_REVIEW_DELTA_DAYS, _MAX_REVIEW_DELTA_DAYS)
        reviewed_at = submitted_at + timedelta(days=review_delta)

        rows.append({
            "review_id":             len(rows) + 1,
            "appeal_id":             appeal_id,
            "reviewer_id":           reviewer_id,
            "outcome":               appeal_status,   # matches appeal_status exactly
            "rationale":             faker.sentence(),
            "independence_verified": True,
            "reviewed_at":           reviewed_at,
        })

    # ----------------------------------------------------------------
    # 7. Phase B — Fill remaining slots from optional appeals to reach ~80
    # ----------------------------------------------------------------
    remaining = TARGET_APPEAL_REVIEWS - len(rows)

    if remaining > 0 and len(optional_appeals) > 0:
        # Sample WITH replacement if we need more rows than available optional appeals
        if remaining <= len(optional_appeals):
            sampled_indices = rng.sample(range(len(optional_appeals)), remaining)
            sampled_optional = optional_appeals.iloc[sampled_indices]
        else:
            # Wrap around with replacement
            sampled_indices = rng.choices(range(len(optional_appeals)), k=remaining)
            sampled_optional = optional_appeals.iloc[sampled_indices]

        for _, appeal_row in sampled_optional.iterrows():
            appeal_id = appeal_row["appeal_id"]
            case_id = appeal_row["case_id"]
            submitted_at = _to_datetime(appeal_row["submitted_at"])

            reviewer_id = _pick_reviewer(case_id)

            review_delta = rng.randint(_MIN_REVIEW_DELTA_DAYS, _MAX_REVIEW_DELTA_DAYS)
            reviewed_at = submitted_at + timedelta(days=review_delta)

            outcome = rng.choices(
                _OPTIONAL_OUTCOME_VALUES, weights=_OPTIONAL_OUTCOME_WEIGHTS, k=1
            )[0]

            rows.append({
                "review_id":             len(rows) + 1,
                "appeal_id":             appeal_id,
                "reviewer_id":           reviewer_id,
                "outcome":               outcome,
                "rationale":             faker.sentence(),
                "independence_verified": False,
                "reviewed_at":           reviewed_at,
            })

    # ----------------------------------------------------------------
    # 8. Assemble DataFrame
    # ----------------------------------------------------------------
    df = pd.DataFrame(rows, columns=[
        "review_id",
        "appeal_id",
        "reviewer_id",
        "outcome",
        "rationale",
        "independence_verified",
        "reviewed_at",
    ])

    # ----------------------------------------------------------------
    # 9. Sanity assertions
    # ----------------------------------------------------------------

    # Row count should be approximately TARGET_APPEAL_REVIEWS (80)
    assert _MIN_ROWS <= len(df) <= _MAX_ROWS, (
        f"Expected approximately {TARGET_APPEAL_REVIEWS} AppealReview rows "
        f"({_MIN_ROWS}–{_MAX_ROWS}), got {len(df)}"
    )

    # review_id must be sequential integers starting at 1
    assert list(df["review_id"]) == list(range(1, len(df) + 1)), (
        "review_id must be a sequential integer series starting at 1"
    )

    # All outcome values must be valid enum members
    assert df["outcome"].isin(_VALID_OUTCOMES).all(), (
        "All outcome values must be UPHELD, OVERTURNED, or REMANDED"
    )

    # All UPHELD/OVERTURNED appeals must have at least one row with independence_verified = True
    resolved_appeal_ids = set(
        appeals_df.loc[
            appeals_df["appeal_status"].isin(_RESOLVED_STATUSES), "appeal_id"
        ]
    )
    if resolved_appeal_ids:
        verified_df = df[df["independence_verified"] == True]  # noqa: E712
        verified_appeal_ids = set(verified_df["appeal_id"])
        missing_verified = resolved_appeal_ids - verified_appeal_ids
        assert not missing_verified, (
            f"The following UPHELD/OVERTURNED appeal_ids lack a review row with "
            f"independence_verified = True: {sorted(missing_verified)[:10]}"
        )

    # No reviewer_id should match the PRIMARY CaseReviewer for that appeal's case
    appeal_case_map = dict(zip(appeals_df["appeal_id"], appeals_df["case_id"]))
    for _, review_row in df.iterrows():
        appeal_id = review_row["appeal_id"]
        reviewer_id = review_row["reviewer_id"]
        case_id = appeal_case_map.get(appeal_id)
        if case_id is not None:
            primary_rev = primary_reviewer_map.get(case_id)
            assert reviewer_id != primary_rev, (
                f"review_id={review_row['review_id']}: reviewer_id={reviewer_id} "
                f"matches the PRIMARY CaseReviewer for case_id={case_id}"
            )

    # reviewed_at must be after submitted_at for the linked appeal
    submitted_map = dict(
        zip(appeals_df["appeal_id"], pd.to_datetime(appeals_df["submitted_at"]))
    )
    reviewed_arr = pd.to_datetime(df["reviewed_at"])
    submitted_arr = df["appeal_id"].map(submitted_map)
    assert (reviewed_arr > submitted_arr).all(), (
        "reviewed_at must be strictly after the corresponding appeal's submitted_at"
    )

    return df
