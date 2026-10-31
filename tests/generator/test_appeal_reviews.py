"""
Tests for the AppealReview data generator.

Validates:

  Requirements 5.2, 5.3, 5.4

  - Approximately 80 rows are generated (between 70 and 90)
  - Every UPHELD/OVERTURNED appeal has at least one row with
    independence_verified = True
  - No reviewer_id matches the PRIMARY CaseReviewer for that appeal's case
  - All outcome values are valid enum members
  - reviewed_at is strictly after the appeal's submitted_at

Feature: academic-integrity-system
"""

import random

import numpy as np
import pandas as pd
import pytest
from faker import Faker

from data_generator.config import SEED, TARGET_APPEAL_REVIEWS
from data_generator.generators.appeals import generate_appeals
from data_generator.generators.appeal_reviews import generate_appeal_reviews
from data_generator.generators.assessments import generate_assessments
from data_generator.generators.case_reviewers import generate_case_reviewers
from data_generator.generators.decisions import generate_decisions
from data_generator.generators.integrity_cases import generate_integrity_cases
from data_generator.generators.integrity_rules import generate_integrity_rules
from data_generator.generators.learners import generate_learners
from data_generator.generators.reviewers import generate_reviewers
from data_generator.generators.similarity_reports import generate_similarity_reports
from data_generator.generators.submissions import generate_submissions


_VALID_OUTCOMES = {"UPHELD", "OVERTURNED", "REMANDED"}
_RESOLVED_STATUSES = {"UPHELD", "OVERTURNED"}


def _init_rng():
    rng = random.Random(SEED)
    nprng = np.random.default_rng(SEED)
    faker = Faker()
    Faker.seed(SEED)
    return rng, nprng, faker


@pytest.fixture(scope="module")
def generated_data():
    """Generate the full chain up through AppealReviews with SEED=20261022."""
    rng, nprng, faker = _init_rng()
    rules_df = generate_integrity_rules(rng)
    learners_df = generate_learners(rng, nprng, faker)
    assessments_df = generate_assessments(rng, faker)
    reviewers_df = generate_reviewers(rng, faker)
    submissions_df = generate_submissions(rng, nprng, learners_df, assessments_df)
    reports_df = generate_similarity_reports(nprng, submissions_df, rules_df)
    cases_df = generate_integrity_cases(rng, reports_df)
    case_reviewers_df = generate_case_reviewers(rng, cases_df, reviewers_df)
    decisions_df = generate_decisions(rng, faker, cases_df, reviewers_df)
    appeals_df = generate_appeals(rng, faker, cases_df, decisions_df, learners_df)
    appeal_reviews_df = generate_appeal_reviews(
        rng, faker, appeals_df, case_reviewers_df, reviewers_df
    )
    return appeals_df, case_reviewers_df, reviewers_df, appeal_reviews_df


# ---------------------------------------------------------------------------
# Row count
# ---------------------------------------------------------------------------


def test_appeal_review_row_count_is_approximately_80(generated_data):
    # Validates: Requirements 5.3
    _, _, _, appeal_reviews_df = generated_data
    count = len(appeal_reviews_df)
    assert 70 <= count <= 90, (
        f"Expected approximately {TARGET_APPEAL_REVIEWS} AppealReview rows "
        f"(70–90), got {count}"
    )


# ---------------------------------------------------------------------------
# review_id is sequential
# ---------------------------------------------------------------------------


def test_review_id_is_sequential_from_one(generated_data):
    # Validates: Requirements 5.3
    _, _, _, appeal_reviews_df = generated_data
    expected = list(range(1, len(appeal_reviews_df) + 1))
    actual = appeal_reviews_df["review_id"].tolist()
    assert actual == expected, (
        "review_id must be a sequential integer series starting at 1"
    )


# ---------------------------------------------------------------------------
# independence_verified constraint
# ---------------------------------------------------------------------------


def test_upheld_overturned_appeals_have_independence_verified(generated_data):
    # Validates: Requirements 5.2
    appeals_df, _, _, appeal_reviews_df = generated_data

    resolved_ids = set(
        appeals_df.loc[
            appeals_df["appeal_status"].isin(_RESOLVED_STATUSES), "appeal_id"
        ]
    )
    verified_ids = set(
        appeal_reviews_df.loc[
            appeal_reviews_df["independence_verified"] == True, "appeal_id"  # noqa: E712
        ]
    )
    missing = resolved_ids - verified_ids
    assert not missing, (
        f"{len(missing)} UPHELD/OVERTURNED appeal(s) lack a row with "
        f"independence_verified = True: {sorted(missing)[:10]}"
    )


# ---------------------------------------------------------------------------
# Reviewer independence: reviewer ≠ primary case reviewer
# ---------------------------------------------------------------------------


def test_reviewer_differs_from_primary_case_reviewer(generated_data):
    # Validates: Requirements 5.4
    appeals_df, case_reviewers_df, _, appeal_reviews_df = generated_data

    primary_df = case_reviewers_df[case_reviewers_df["assignment_role"] == "PRIMARY"]
    primary_map = dict(zip(primary_df["case_id"], primary_df["reviewer_id"]))
    appeal_case_map = dict(zip(appeals_df["appeal_id"], appeals_df["case_id"]))

    violations = []
    for _, row in appeal_reviews_df.iterrows():
        case_id = appeal_case_map.get(row["appeal_id"])
        if case_id is not None:
            primary_rev = primary_map.get(case_id)
            if row["reviewer_id"] == primary_rev:
                violations.append(row["review_id"])

    assert not violations, (
        f"Found {len(violations)} AppealReview row(s) where reviewer_id matches "
        f"the PRIMARY CaseReviewer: review_id(s) = {violations[:10]}"
    )


# ---------------------------------------------------------------------------
# Valid outcome values
# ---------------------------------------------------------------------------


def test_all_outcomes_are_valid_enum_values(generated_data):
    # Validates: Requirements 5.3
    _, _, _, appeal_reviews_df = generated_data
    invalid = ~appeal_reviews_df["outcome"].isin(_VALID_OUTCOMES)
    assert not invalid.any(), (
        f"Found invalid outcome values: "
        f"{appeal_reviews_df.loc[invalid, 'outcome'].unique().tolist()}"
    )


def test_resolved_appeal_review_outcome_matches_appeal_status(generated_data):
    # Validates: Requirements 5.3
    appeals_df, _, _, appeal_reviews_df = generated_data

    status_map = dict(zip(appeals_df["appeal_id"], appeals_df["appeal_status"]))
    verified_df = appeal_reviews_df[appeal_reviews_df["independence_verified"] == True]  # noqa: E712

    for _, row in verified_df.iterrows():
        appeal_status = status_map.get(row["appeal_id"])
        if appeal_status in _RESOLVED_STATUSES:
            assert row["outcome"] == appeal_status, (
                f"review_id={row['review_id']}: outcome={row['outcome']} does not "
                f"match appeal_status={appeal_status}"
            )


# ---------------------------------------------------------------------------
# reviewed_at > submitted_at
# ---------------------------------------------------------------------------


def test_reviewed_at_is_after_submitted_at(generated_data):
    # Validates: Requirements 5.3
    appeals_df, _, _, appeal_reviews_df = generated_data

    submitted_map = dict(
        zip(appeals_df["appeal_id"], pd.to_datetime(appeals_df["submitted_at"]))
    )
    reviewed_arr = pd.to_datetime(appeal_reviews_df["reviewed_at"])
    submitted_arr = appeal_reviews_df["appeal_id"].map(submitted_map)

    bad = reviewed_arr <= submitted_arr
    assert not bad.any(), (
        f"Found {bad.sum()} AppealReview row(s) where reviewed_at is not "
        f"strictly after submitted_at."
    )


# ---------------------------------------------------------------------------
# reviewer_id references a valid reviewer
# ---------------------------------------------------------------------------


def test_reviewer_id_references_valid_reviewer(generated_data):
    # Validates: Requirements 5.3
    _, _, reviewers_df, appeal_reviews_df = generated_data

    valid_ids = set(reviewers_df["reviewer_id"])
    invalid = ~appeal_reviews_df["reviewer_id"].isin(valid_ids)
    assert not invalid.any(), (
        f"Found {invalid.sum()} AppealReview row(s) with invalid reviewer_id."
    )


# ---------------------------------------------------------------------------
# appeal_id references a valid appeal
# ---------------------------------------------------------------------------


def test_appeal_id_references_valid_appeal(generated_data):
    # Validates: Requirements 5.3
    appeals_df, _, _, appeal_reviews_df = generated_data

    valid_ids = set(appeals_df["appeal_id"])
    invalid = ~appeal_reviews_df["appeal_id"].isin(valid_ids)
    assert not invalid.any(), (
        f"Found {invalid.sum()} AppealReview row(s) with invalid appeal_id."
    )
