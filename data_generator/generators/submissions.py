"""
Generator for Submission data.

Produces exactly 10,000 Submission rows with FK-safe references to Learner
and Assessment parent tables.  The triple (learner_id, assessment_id,
attempt_no) is unique for every row, matching the ``uq_submission_attempt``
constraint in database/schema.sql.

All columns match the ``Submission`` table defined in database/schema.sql.
"""

import hashlib
import random

import numpy as np
import pandas as pd
from datetime import datetime

from data_generator.utils.id_formatter import fmt_submission
from data_generator.utils.date_utils import random_datetime

# Submission date range — all submissions fall within the 2026 academic year.
_SUBMITTED_AT_START = datetime(2026, 1, 15, 8, 0, 0)
_SUBMITTED_AT_END   = datetime(2026, 12, 10, 23, 59, 59)

# Status distribution weights: SUBMITTED is the overwhelming majority;
# a small fraction are LATE or WITHDRAWN.
_STATUSES  = ["SUBMITTED", "LATE", "WITHDRAWN"]
_STATUS_WEIGHTS = [0.88, 0.09, 0.03]

# Year used for submission ID formatting.
_YEAR = 2026


def _make_content_hash(submission_id: str) -> str:
    """Return a deterministic SHA-256 hex digest for a submission.

    The hash is derived solely from the ``submission_id`` so it is
    reproducible across runs without consuming RNG state.
    """
    return hashlib.sha256(submission_id.encode()).hexdigest()


def generate_submissions(rng, nprng, learners_df: pd.DataFrame, assessments_df: pd.DataFrame) -> pd.DataFrame:
    """Generate exactly 10,000 Submission rows.

    Parameters
    ----------
    rng:
        ``random.Random`` instance seeded externally — used for
        ``submitted_at``, ``status``, and ``content_reference`` selection.
    nprng:
        ``numpy.random.Generator`` instance seeded externally — used for
        vectorised FK sampling (``learner_id`` and ``assessment_id``).
    learners_df:
        DataFrame produced by ``generate_learners()``; must contain a
        ``learner_id`` column.
    assessments_df:
        DataFrame produced by ``generate_assessments()``; must contain an
        ``assessment_id`` column.

    Returns
    -------
    pd.DataFrame
        Columns: submission_id, learner_id, assessment_id, attempt_no,
                 submitted_at, content_reference, content_hash, status

    Notes
    -----
    The triple (learner_id, assessment_id, attempt_no) is unique for every
    row.  The first submission by a given learner for a given assessment
    receives ``attempt_no = 1``; subsequent submissions to the same pair
    receive incrementing attempt numbers.
    """
    n = 10_000
    learner_ids    = learners_df["learner_id"].tolist()
    assessment_ids = assessments_df["assessment_id"].tolist()

    # attempt_tracker maps (learner_id, assessment_id) -> current attempt_no
    attempt_tracker: dict[tuple[str, str], int] = {}

    rows = []

    for i in range(1, n + 1):
        submission_id = fmt_submission(_YEAR, i)

        # --- FK-safe sampling -------------------------------------------
        # Sample learner and assessment independently.  On the rare occasion
        # a learner submits to the same assessment multiple times we simply
        # increment the attempt counter — the uniqueness constraint is
        # maintained via attempt_tracker.
        learner_id    = rng.choice(learner_ids)
        assessment_id = rng.choice(assessment_ids)

        # --- attempt_no --------------------------------------------------
        pair = (learner_id, assessment_id)
        attempt_no = attempt_tracker.get(pair, 0) + 1
        attempt_tracker[pair] = attempt_no

        # --- submitted_at ------------------------------------------------
        submitted_at = random_datetime(rng, _SUBMITTED_AT_START, _SUBMITTED_AT_END)

        # --- status ------------------------------------------------------
        status = rng.choices(_STATUSES, weights=_STATUS_WEIGHTS, k=1)[0]

        # --- content_reference -------------------------------------------
        # A lightweight file-path reference; deterministic given the ID.
        content_reference = f"uploads/2026/{submission_id}.pdf"

        # --- content_hash ------------------------------------------------
        # SHA-256 of the submission_id — deterministic, no RNG consumed.
        content_hash = _make_content_hash(submission_id)

        rows.append({
            "submission_id":     submission_id,
            "learner_id":        learner_id,
            "assessment_id":     assessment_id,
            "attempt_no":        attempt_no,
            "submitted_at":      submitted_at,
            "content_reference": content_reference,
            "content_hash":      content_hash,
            "status":            status,
        })

    df = pd.DataFrame(rows, columns=[
        "submission_id",
        "learner_id",
        "assessment_id",
        "attempt_no",
        "submitted_at",
        "content_reference",
        "content_hash",
        "status",
    ])

    # ------------------------------------------------------------------
    # Sanity assertions — catch logic errors before writing to disk.
    # ------------------------------------------------------------------
    assert len(df) == n, f"Expected {n} Submission rows, got {len(df)}"

    assert df["submission_id"].iloc[0] == "SUB-2026-000001", \
        "First submission_id must be SUB-2026-000001"
    assert df["submission_id"].iloc[-1] == "SUB-2026-010000", \
        "Last submission_id must be SUB-2026-010000"

    # FK referential integrity
    valid_learners    = set(learner_ids)
    valid_assessments = set(assessment_ids)
    assert df["learner_id"].isin(valid_learners).all(), \
        "All learner_id values must reference a valid Learner row"
    assert df["assessment_id"].isin(valid_assessments).all(), \
        "All assessment_id values must reference a valid Assessment row"

    # Composite uniqueness: (learner_id, assessment_id, attempt_no)
    composite_key = df[["learner_id", "assessment_id", "attempt_no"]]
    assert composite_key.duplicated().sum() == 0, \
        "(learner_id, assessment_id, attempt_no) must be unique across all rows"

    # attempt_no must be >= 1
    assert (df["attempt_no"] >= 1).all(), "attempt_no must be >= 1 for every row"

    # Dates within the expected range
    assert (df["submitted_at"] >= _SUBMITTED_AT_START).all(), \
        "All submitted_at values must be >= 2026-01-15"
    assert (df["submitted_at"] <= _SUBMITTED_AT_END).all(), \
        "All submitted_at values must be <= 2026-12-10"

    # Status values must be valid enum members
    assert df["status"].isin(_STATUSES).all(), \
        "All status values must be in the allowed enum set"

    return df
