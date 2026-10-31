"""
Generator for SimilarityReport data.

Produces exactly 10,000 SimilarityReport rows — one per Submission row.
Score distribution is bimodal: ~9,000 low scores drawn from a beta
distribution and ~1,000 flagged scores drawn from a uniform distribution.

``report_status`` and ``rule_id`` are derived by matching each score against
the four primary IntegrityRule ranges (RULE-001 through RULE-004).

All columns match the ``SimilarityReport`` table defined in
database/schema.sql.
"""

import numpy as np
import pandas as pd
from datetime import datetime

from data_generator.utils.id_formatter import fmt_report

# Fixed timestamp applied to every generated report.
_GENERATED_AT = datetime(2026, 1, 14, 0, 0, 0)

# Every report is the first (and only) report for its submission.
_REPORT_NO = 1

# Similarity score thresholds that mirror the four-tier IntegrityRule ladder.
# Scores at or above this value set review_required = True.
_REVIEW_THRESHOLD = 71.0

# Mapping from primary-rule action_type → report_status enum value.
# The SimilarityReport.report_status column is:
#   ENUM('GENERATED', 'REVIEW_REQUIRED', 'MONITOR', 'NO_REVIEW')
# HIGH_PRIORITY_REVIEW (RULE-004 action) maps to 'REVIEW_REQUIRED' because
# the schema enum has no 'HIGH_PRIORITY_REVIEW' value.
_ACTION_TO_STATUS = {
    "NO_REVIEW":           "NO_REVIEW",
    "MONITOR":             "MONITOR",
    "REVIEW":              "REVIEW_REQUIRED",
    "HIGH_PRIORITY_REVIEW": "REVIEW_REQUIRED",
}

# Number of low-scoring and flagged rows.
_N_TOTAL   = 10_000
_N_FLAGGED = 1_000
_N_LOW     = _N_TOTAL - _N_FLAGGED  # 9,000


def _derive_status_and_rule(score: float, primary_rules: list[dict]) -> tuple[str, str]:
    """Return (report_status, rule_id) for *score* using the primary rules.

    Parameters
    ----------
    score:
        Clipped similarity score in [0.0, 100.0].
    primary_rules:
        List of dicts with keys ``rule_id``, ``min_similarity``,
        ``max_similarity``, ``action_type`` — one entry per primary rule,
        ordered by priority ascending (RULE-001, RULE-002, RULE-003,
        RULE-004).

    Returns
    -------
    tuple[str, str]
        ``(report_status, rule_id)``

    Notes
    -----
    The primary rules have integer boundaries (0–40, 41–70, 71–85, 86–100)
    but similarity scores are decimal.  Gaps between adjacent rules (e.g.
    40.01–40.99) are resolved by assigning the score to the lower-tier rule
    (i.e. the rule whose ``max_similarity`` is nearest from below).  For the
    last rule we simply accept any score up to 100.
    """
    for idx, rule in enumerate(primary_rules):
        is_last = idx == len(primary_rules) - 1
        if is_last:
            # Last rule: everything from this rule's min up to 100.
            if score >= rule["min_similarity"]:
                return _ACTION_TO_STATUS[rule["action_type"]], rule["rule_id"]
        else:
            next_rule = primary_rules[idx + 1]
            # Score belongs to this tier if it is below the *next* tier's
            # min_similarity threshold, using the review threshold (71.0) as
            # the hard boundary between non-flagged and flagged tiers.
            if score < next_rule["min_similarity"]:
                return _ACTION_TO_STATUS[rule["action_type"]], rule["rule_id"]
    # Fallback — should never be reached given clipped scores in [0, 100].
    return "GENERATED", primary_rules[-1]["rule_id"]


def generate_similarity_reports(
    nprng,
    submissions_df: pd.DataFrame,
    rules_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate exactly 10,000 SimilarityReport rows, one per submission.

    Parameters
    ----------
    nprng:
        ``numpy.random.Generator`` instance seeded externally.  *All*
        randomness flows through this object.
    submissions_df:
        DataFrame produced by ``generate_submissions()``; must contain a
        ``submission_id`` column.  Exactly 10,000 rows are expected.
    rules_df:
        DataFrame produced by ``generate_integrity_rules()``; must contain
        columns ``rule_id``, ``rule_name``, ``min_similarity``,
        ``max_similarity``, ``action_type``, ``priority``.

    Returns
    -------
    pd.DataFrame
        Columns: report_id, submission_id, rule_id, report_no,
                 similarity_score, matched_source_count, review_required,
                 report_status, generated_at
    """
    # ------------------------------------------------------------------
    # 1. Extract primary rules (RULE-001 through RULE-004, priority 1-4)
    # ------------------------------------------------------------------
    primary_rules_df = (
        rules_df[rules_df["priority"].isin([1, 2, 3, 4])]
        .sort_values("priority")
        .reset_index(drop=True)
    )
    primary_rules = primary_rules_df.to_dict("records")

    # ------------------------------------------------------------------
    # 2. Generate the bimodal score distribution
    # ------------------------------------------------------------------
    # Low scores: beta(1.5, 5.0) scaled to 0–85 range (~9,000 rows)
    low_scores  = nprng.beta(a=1.5, b=5.0, size=_N_LOW) * 85.0

    # Flagged scores: uniform 71–100 (~1,000 rows)
    high_scores = nprng.uniform(71.0, 100.0, size=_N_FLAGGED)

    # Concatenate and shuffle in-place (consumes nprng state)
    all_scores = np.concatenate([low_scores, high_scores])
    nprng.shuffle(all_scores)

    # Round to 2 decimal places and clip to [0, 100]
    all_scores = np.clip(np.round(all_scores, 2), 0.0, 100.0)

    # ------------------------------------------------------------------
    # 3. Build rows
    # ------------------------------------------------------------------
    submission_ids = submissions_df["submission_id"].tolist()

    rows = []
    for i, (submission_id, score) in enumerate(zip(submission_ids, all_scores)):
        score_f = float(score)

        report_id  = fmt_report(submission_id, _REPORT_NO)
        report_no  = _REPORT_NO

        review_required = bool(score_f >= _REVIEW_THRESHOLD)

        report_status, rule_id = _derive_status_and_rule(score_f, primary_rules)

        # matched_source_count: proportional to score; flagged reports have
        # more matched sources.  All randomness stays in nprng (scores are
        # already random), so a deterministic formula is used here.
        matched_source_count = max(0, int(score_f / 10))

        rows.append({
            "report_id":           report_id,
            "submission_id":       submission_id,
            "rule_id":             rule_id,
            "report_no":           report_no,
            "similarity_score":    round(score_f, 2),
            "matched_source_count": matched_source_count,
            "review_required":     review_required,
            "report_status":       report_status,
            "generated_at":        _GENERATED_AT,
        })

    # ------------------------------------------------------------------
    # 4. Assemble DataFrame
    # ------------------------------------------------------------------
    df = pd.DataFrame(rows, columns=[
        "report_id",
        "submission_id",
        "rule_id",
        "report_no",
        "similarity_score",
        "matched_source_count",
        "review_required",
        "report_status",
        "generated_at",
    ])

    # ------------------------------------------------------------------
    # 5. Sanity assertions
    # ------------------------------------------------------------------
    assert len(df) == _N_TOTAL, \
        f"Expected {_N_TOTAL} SimilarityReport rows, got {len(df)}"

    # One report per submission — no duplicates
    assert df["submission_id"].is_unique, \
        "Each submission must have exactly one SimilarityReport row"

    # All submission_ids must come from submissions_df
    valid_subs = set(submission_ids)
    assert df["submission_id"].isin(valid_subs).all(), \
        "All submission_id values must reference a valid Submission row"

    # Score bounds
    assert (df["similarity_score"] >= 0.0).all() and \
           (df["similarity_score"] <= 100.0).all(), \
        "All similarity_score values must be in [0.00, 100.00]"

    # review_required consistency
    flagged_mask = df["similarity_score"] >= _REVIEW_THRESHOLD
    assert (df.loc[flagged_mask,  "review_required"] == True).all(), \
        "review_required must be True when similarity_score >= 71.0"
    assert (df.loc[~flagged_mask, "review_required"] == False).all(), \
        "review_required must be False when similarity_score < 71.0"

    # report_status must be a valid enum value
    valid_statuses = {"GENERATED", "REVIEW_REQUIRED", "MONITOR", "NO_REVIEW"}
    assert df["report_status"].isin(valid_statuses).all(), \
        "All report_status values must be valid enum members"

    # rule_id must reference a primary rule
    valid_rule_ids = set(primary_rules_df["rule_id"])
    assert df["rule_id"].isin(valid_rule_ids).all(), \
        "All rule_id values must reference a primary IntegrityRule row"

    # report_no is always 1
    assert (df["report_no"] == _REPORT_NO).all(), \
        "report_no must be 1 for every row"

    return df
