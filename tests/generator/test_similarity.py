"""
Property tests for the SimilarityReport data generator.

Validates three properties:

  Property 5: SimilarityReport 1:1 with Submission
    Each submission_id appears exactly once in the SimilarityReport DataFrame
    and every submission_id value exists in the Submission DataFrame.

  Property 6: Report status derived from rule
    For every row the report_status is consistent with the similarity_score
    mapped through the IntegrityRule ranges:
      score < 41            → NO_REVIEW
      41 ≤ score < 71       → MONITOR
      71 ≤ score < 86       → REVIEW_REQUIRED
      score ≥ 86            → REVIEW_REQUIRED

  Property 7: Similarity score bounds
    For all rows 0.00 ≤ similarity_score ≤ 100.00.

Feature: academic-integrity-system
"""

import random

import numpy as np
import pytest
from faker import Faker

from data_generator.config import SEED, TARGET_REPORTS
from data_generator.generators.assessments import generate_assessments
from data_generator.generators.integrity_rules import generate_integrity_rules
from data_generator.generators.learners import generate_learners
from data_generator.generators.similarity_reports import generate_similarity_reports
from data_generator.generators.submissions import generate_submissions


def _init_rng():
    """Initialise all RNG sources with the fixed project seed."""
    rng = random.Random(SEED)
    nprng = np.random.default_rng(SEED)
    faker = Faker()
    Faker.seed(SEED)
    return rng, nprng, faker


# ---------------------------------------------------------------------------
# Module-scoped fixture — data generated once for all tests in this module
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def generated_data():
    """Generate all prerequisite DataFrames and the SimilarityReport DataFrame."""
    rng, nprng, faker = _init_rng()
    rules_df = generate_integrity_rules(rng)
    learners_df = generate_learners(rng, nprng, faker)
    assessments_df = generate_assessments(rng, faker)
    submissions_df = generate_submissions(rng, nprng, learners_df, assessments_df)
    reports_df = generate_similarity_reports(nprng, submissions_df, rules_df)
    return submissions_df, reports_df


# ---------------------------------------------------------------------------
# Property 5: SimilarityReport 1:1 with Submission
# ---------------------------------------------------------------------------

def test_each_submission_id_appears_exactly_once(generated_data):
    # Feature: academic-integrity-system, Property 5: SimilarityReport 1:1 with Submission
    submissions_df, reports_df = generated_data

    duplicates = reports_df["submission_id"].duplicated()
    assert not duplicates.any(), (
        f"Found {duplicates.sum()} duplicate submission_id value(s) in "
        f"SimilarityReport DataFrame: "
        f"{reports_df.loc[duplicates, 'submission_id'].tolist()}"
    )


def test_all_submission_ids_exist_in_submission_dataframe(generated_data):
    # Feature: academic-integrity-system, Property 5: SimilarityReport 1:1 with Submission
    submissions_df, reports_df = generated_data

    valid_ids = set(submissions_df["submission_id"])
    orphaned = ~reports_df["submission_id"].isin(valid_ids)
    assert not orphaned.any(), (
        f"Found {orphaned.sum()} SimilarityReport row(s) whose submission_id "
        f"does not exist in the Submission DataFrame: "
        f"{reports_df.loc[orphaned, 'submission_id'].tolist()}"
    )


def test_report_row_count_matches_submission_row_count(generated_data):
    # Feature: academic-integrity-system, Property 5: SimilarityReport 1:1 with Submission
    submissions_df, reports_df = generated_data

    assert len(reports_df) == len(submissions_df) == TARGET_REPORTS, (
        f"Expected {TARGET_REPORTS} SimilarityReport rows (one per Submission), "
        f"got reports={len(reports_df)}, submissions={len(submissions_df)}"
    )


# ---------------------------------------------------------------------------
# Property 6: Report status derived from rule
# ---------------------------------------------------------------------------

def _expected_status(score: float) -> str:
    """Mirror the four-tier rule ladder used by the generator."""
    if score < 41.0:
        return "NO_REVIEW"
    elif score < 71.0:
        return "MONITOR"
    else:
        # 71 ≤ score ≤ 100 → REVIEW_REQUIRED
        # (covers both RULE-003 and HIGH_PRIORITY_REVIEW / RULE-004)
        return "REVIEW_REQUIRED"


def test_report_status_consistent_with_similarity_score(generated_data):
    # Feature: academic-integrity-system, Property 6: Report status derived from rule
    _submissions_df, reports_df = generated_data

    mismatches = reports_df.apply(
        lambda row: row["report_status"] != _expected_status(row["similarity_score"]),
        axis=1,
    )
    if mismatches.any():
        bad = reports_df.loc[mismatches, ["submission_id", "similarity_score", "report_status"]].head(10)
        raise AssertionError(
            f"Found {mismatches.sum()} row(s) where report_status does not match "
            f"the expected status derived from similarity_score.\n"
            f"First offending rows (showing up to 10):\n{bad.to_string(index=False)}"
        )


def test_no_review_status_only_for_scores_below_41(generated_data):
    # Feature: academic-integrity-system, Property 6: Report status derived from rule
    _submissions_df, reports_df = generated_data

    no_review_rows = reports_df[reports_df["report_status"] == "NO_REVIEW"]
    bad = no_review_rows[no_review_rows["similarity_score"] >= 41.0]
    assert bad.empty, (
        f"Found {len(bad)} NO_REVIEW row(s) with similarity_score >= 41.0: "
        f"{bad[['submission_id', 'similarity_score']].to_string(index=False)}"
    )


def test_monitor_status_only_for_scores_in_41_to_70(generated_data):
    # Feature: academic-integrity-system, Property 6: Report status derived from rule
    _submissions_df, reports_df = generated_data

    monitor_rows = reports_df[reports_df["report_status"] == "MONITOR"]
    bad_low  = monitor_rows[monitor_rows["similarity_score"] < 41.0]
    bad_high = monitor_rows[monitor_rows["similarity_score"] >= 71.0]
    assert bad_low.empty and bad_high.empty, (
        f"Found MONITOR rows outside the 41–70 range: "
        f"below 41: {len(bad_low)}, at/above 71: {len(bad_high)}"
    )


def test_review_required_status_only_for_scores_at_or_above_71(generated_data):
    # Feature: academic-integrity-system, Property 6: Report status derived from rule
    _submissions_df, reports_df = generated_data

    rr_rows = reports_df[reports_df["report_status"] == "REVIEW_REQUIRED"]
    bad = rr_rows[rr_rows["similarity_score"] < 71.0]
    assert bad.empty, (
        f"Found {len(bad)} REVIEW_REQUIRED row(s) with similarity_score < 71.0: "
        f"{bad[['submission_id', 'similarity_score']].to_string(index=False)}"
    )


# ---------------------------------------------------------------------------
# Property 7: Similarity score bounds
# ---------------------------------------------------------------------------

def test_similarity_scores_are_within_bounds(generated_data):
    # Feature: academic-integrity-system, Property 7: Similarity score bounds
    _submissions_df, reports_df = generated_data

    below_zero = reports_df[reports_df["similarity_score"] < 0.00]
    above_hundred = reports_df[reports_df["similarity_score"] > 100.00]

    assert below_zero.empty, (
        f"Found {len(below_zero)} row(s) with similarity_score < 0.00: "
        f"{below_zero[['submission_id', 'similarity_score']].to_string(index=False)}"
    )
    assert above_hundred.empty, (
        f"Found {len(above_hundred)} row(s) with similarity_score > 100.00: "
        f"{above_hundred[['submission_id', 'similarity_score']].to_string(index=False)}"
    )


def test_similarity_scores_are_rounded_to_two_decimal_places(generated_data):
    # Feature: academic-integrity-system, Property 7: Similarity score bounds
    _submissions_df, reports_df = generated_data

    # A score rounded to 2 dp satisfies: round(score, 2) == score
    bad = reports_df[
        reports_df["similarity_score"].apply(lambda s: round(s, 2) != s)
    ]
    assert bad.empty, (
        f"Found {len(bad)} row(s) whose similarity_score has more than 2 decimal places: "
        f"{bad[['submission_id', 'similarity_score']].head(10).to_string(index=False)}"
    )
