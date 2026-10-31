"""
Generator for CaseReviewer bridge data.

Produces approximately 350 CaseReviewer rows covering:

  1. Exactly one ``assignment_role = 'PRIMARY'`` row per IntegrityCase (300 rows).
  2. Approximately 50 additional SECONDARY / INDEPENDENT_APPEAL rows spread
     across randomly sampled cases to reach ~350 total.
  3. At least 10 rows with ``conflict_status = 'CONFLICT'``, each carrying a
     non-null, non-empty ``conflict_reason``; these rows have ``unassigned_at``
     set.  Non-CONFLICT rows have ``unassigned_at = None``.

All columns match the ``CaseReviewer`` table defined in ``database/schema.sql``.

Columns produced
----------------
assignment_id   – sequential integer starting at 1 (mirrors AUTO_INCREMENT PK)
case_id         – FK → IntegrityCase
reviewer_id     – FK → Reviewer
assignment_role – ENUM: PRIMARY, SECONDARY, INDEPENDENT_APPEAL
conflict_status – ENUM: PENDING, CLEARED, CONFLICT   (default PENDING for non-CONFLICT)
conflict_reason – TEXT, nullable; required for CONFLICT rows
assigned_at     – case ``opened_at`` + 1–3 days
unassigned_at   – ``assigned_at`` + 2–7 days (CONFLICT rows only); NULL otherwise
"""

import random
from datetime import timedelta

import pandas as pd

from data_generator.config import TARGET_CASES, TARGET_REVIEWERS_ASSIGNED

# ------------------------------------------------------------------ #
# Constants                                                            #
# ------------------------------------------------------------------ #

# Roles available for the ~50 extra (non-PRIMARY) assignments.
_EXTRA_ROLES = ["SECONDARY", "INDEPENDENT_APPEAL"]

# Minimum number of CONFLICT rows required.
_MIN_CONFLICT_ROWS = 10

# Days after case opened_at that the reviewer is assigned (1–3 inclusive).
_MIN_ASSIGN_DELTA_DAYS = 1
_MAX_ASSIGN_DELTA_DAYS = 3

# Days after assigned_at that a CONFLICT reviewer is unassigned (2–7 inclusive).
_MIN_UNASSIGN_DELTA_DAYS = 2
_MAX_UNASSIGN_DELTA_DAYS = 7

# Number of extra (non-PRIMARY) rows to add on top of the 300 PRIMARY rows.
# TARGET_REVIEWERS_ASSIGNED (350) - TARGET_CASES (300) = 50
_EXTRA_ROWS = TARGET_REVIEWERS_ASSIGNED - TARGET_CASES   # 50

# Canned conflict reasons for realism.
_CONFLICT_REASONS = [
    "Prior supervisory relationship with the student",
    "Personal acquaintance with the learner outside of academic context",
    "Co-authored publication with the learner within the last 24 months",
    "Family or close personal relationship with the learner",
    "Financial interest in the learner's programme outcome",
    "Previous advisory role for the learner's research project",
    "Witnessed the submission event and may be called as a witness",
    "Served as external examiner for the learner's prior institution",
    "Involved in an unresolved complaint filed by the learner",
    "Prior employment relationship with the learner",
    "Named as a reference on the learner's academic record",
    "Ongoing mentorship relationship with the learner",
]


# ------------------------------------------------------------------ #
# Public API                                                           #
# ------------------------------------------------------------------ #


def generate_case_reviewers(
    rng: random.Random,
    cases_df: pd.DataFrame,
    reviewers_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate approximately 350 CaseReviewer rows.

    Parameters
    ----------
    rng:
        ``random.Random`` instance seeded externally.  All randomness
        flows through this object — no new random sources are created.
    cases_df:
        DataFrame produced by ``generate_integrity_cases()``; must
        contain columns ``case_id`` and ``opened_at``.
    reviewers_df:
        DataFrame produced by ``generate_reviewers()``; must contain
        column ``reviewer_id``.

    Returns
    -------
    pd.DataFrame
        Columns: assignment_id, case_id, reviewer_id, assignment_role,
                 conflict_status, conflict_reason, assigned_at, unassigned_at
    """
    reviewer_ids: list[str] = reviewers_df["reviewer_id"].tolist()
    case_ids:     list[str] = cases_df["case_id"].tolist()

    # Build a quick lookup: case_id → opened_at (as Python datetime)
    opened_at_map: dict[str, object] = {}
    for _, row in cases_df.iterrows():
        ts = row["opened_at"]
        if hasattr(ts, "to_pydatetime"):
            ts = ts.to_pydatetime()
        opened_at_map[row["case_id"]] = ts

    rows: list[dict] = []
    assignment_id = 0

    # ------------------------------------------------------------------
    # Phase 1 — PRIMARY assignment for every case (300 rows)
    # ------------------------------------------------------------------
    for case_id in case_ids:
        assignment_id += 1
        reviewer_id = rng.choice(reviewer_ids)
        opened_at   = opened_at_map[case_id]

        assign_delta = rng.randint(_MIN_ASSIGN_DELTA_DAYS, _MAX_ASSIGN_DELTA_DAYS)
        assigned_at  = opened_at + timedelta(days=assign_delta)

        rows.append({
            "assignment_id":   assignment_id,
            "case_id":         case_id,
            "reviewer_id":     reviewer_id,
            "assignment_role": "PRIMARY",
            "conflict_status": "PENDING",
            "conflict_reason": None,
            "assigned_at":     assigned_at,
            "unassigned_at":   None,
        })

    # ------------------------------------------------------------------
    # Phase 2 — Extra SECONDARY / INDEPENDENT_APPEAL rows (~50 rows)
    # ------------------------------------------------------------------
    # Sample cases WITH replacement so multiple extras can hit the same case.
    extra_case_ids = rng.choices(case_ids, k=_EXTRA_ROWS)

    for case_id in extra_case_ids:
        assignment_id += 1
        reviewer_id   = rng.choice(reviewer_ids)
        role          = rng.choice(_EXTRA_ROLES)
        opened_at     = opened_at_map[case_id]

        assign_delta = rng.randint(_MIN_ASSIGN_DELTA_DAYS, _MAX_ASSIGN_DELTA_DAYS)
        assigned_at  = opened_at + timedelta(days=assign_delta)

        rows.append({
            "assignment_id":   assignment_id,
            "case_id":         case_id,
            "reviewer_id":     reviewer_id,
            "assignment_role": role,
            "conflict_status": "PENDING",
            "conflict_reason": None,
            "assigned_at":     assigned_at,
            "unassigned_at":   None,
        })

    # ------------------------------------------------------------------
    # Phase 3 — Mark exactly _MIN_CONFLICT_ROWS rows as CONFLICT
    #
    # Prefer non-PRIMARY rows (indices 300..349) so the PRIMARY
    # assignments are not marked as conflicts (cleaner data model).
    # Fall back to PRIMARY rows only if there are not enough extras.
    # ------------------------------------------------------------------
    extra_indices   = list(range(TARGET_CASES, len(rows)))        # 300–349
    primary_indices = list(range(0, TARGET_CASES))               # 0–299

    # We need _MIN_CONFLICT_ROWS conflict rows; prefer extras first.
    conflict_pool: list[int]
    if len(extra_indices) >= _MIN_CONFLICT_ROWS:
        conflict_pool = rng.sample(extra_indices, _MIN_CONFLICT_ROWS)
    else:
        # Not enough extras — draw the remainder from primary indices
        extra_all        = list(extra_indices)
        still_needed     = _MIN_CONFLICT_ROWS - len(extra_all)
        primary_sample   = rng.sample(primary_indices, still_needed)
        conflict_pool    = extra_all + primary_sample

    conflict_reasons = rng.choices(_CONFLICT_REASONS, k=_MIN_CONFLICT_ROWS)

    for pool_pos, row_idx in enumerate(conflict_pool):
        row            = rows[row_idx]
        assigned_at    = row["assigned_at"]

        unassign_delta   = rng.randint(_MIN_UNASSIGN_DELTA_DAYS, _MAX_UNASSIGN_DELTA_DAYS)
        unassigned_at    = assigned_at + timedelta(days=unassign_delta)

        row["conflict_status"] = "CONFLICT"
        row["conflict_reason"] = conflict_reasons[pool_pos]
        row["unassigned_at"]   = unassigned_at

    # ------------------------------------------------------------------
    # Phase 4 — Assemble DataFrame
    # ------------------------------------------------------------------
    df = pd.DataFrame(rows, columns=[
        "assignment_id",
        "case_id",
        "reviewer_id",
        "assignment_role",
        "conflict_status",
        "conflict_reason",
        "assigned_at",
        "unassigned_at",
    ])

    # ------------------------------------------------------------------
    # Phase 5 — Sanity assertions
    # ------------------------------------------------------------------

    # Every case_id must have at least one PRIMARY row.
    primary_df = df[df["assignment_role"] == "PRIMARY"]
    cases_with_primary = set(primary_df["case_id"])
    assert set(case_ids) == cases_with_primary, (
        f"The following case_ids are missing a PRIMARY reviewer: "
        f"{set(case_ids) - cases_with_primary}"
    )

    # At least 10 CONFLICT rows must exist.
    conflict_df = df[df["conflict_status"] == "CONFLICT"]
    assert len(conflict_df) >= _MIN_CONFLICT_ROWS, (
        f"Expected at least {_MIN_CONFLICT_ROWS} CONFLICT rows, got {len(conflict_df)}"
    )

    # All CONFLICT rows must have non-null, non-empty conflict_reason.
    bad_reason_mask = conflict_df["conflict_reason"].isna() | (conflict_df["conflict_reason"] == "")
    assert not bad_reason_mask.any(), (
        f"Found {bad_reason_mask.sum()} CONFLICT row(s) with null or empty conflict_reason"
    )

    # All CONFLICT rows must have non-null unassigned_at.
    assert conflict_df["unassigned_at"].notna().all(), (
        "All CONFLICT rows must have a non-null unassigned_at"
    )

    # All non-CONFLICT rows must have null unassigned_at.
    non_conflict_df = df[df["conflict_status"] != "CONFLICT"]
    assert non_conflict_df["unassigned_at"].isna().all(), (
        "All non-CONFLICT rows must have unassigned_at = None"
    )

    # assignment_id must be a unique sequential integer starting at 1.
    assert df["assignment_id"].iloc[0] == 1, \
        "First assignment_id must be 1"
    assert list(df["assignment_id"]) == list(range(1, len(df) + 1)), \
        "assignment_id must be a sequential integer series starting at 1"

    # Total row count should be approximately TARGET_REVIEWERS_ASSIGNED.
    total = len(df)
    assert total >= TARGET_CASES, (
        f"Must have at least {TARGET_CASES} rows (one PRIMARY per case); got {total}"
    )

    return df
