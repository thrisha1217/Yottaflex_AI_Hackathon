"""
Property tests for the CaseReviewer data generator.

Validates:

  Property 9: Every case has a PRIMARY reviewer
    The CaseReviewer DataFrame contains at least one row with
    assignment_role = 'PRIMARY' for every case_id in the IntegrityCase DataFrame.

  Property 10: CONFLICT rows have non-null reason
    Every row where conflict_status = 'CONFLICT' has a non-empty,
    non-null conflict_reason.

Additional assertions:
  - At least 10 CONFLICT rows exist in total.
  - All CONFLICT rows have non-null unassigned_at.
  - All non-CONFLICT rows have null unassigned_at.

Feature: academic-integrity-system
"""

import random

import numpy as np
import pytest
from faker import Faker

from data_generator.config import SEED
from data_generator.generators.assessments import generate_assessments
from data_generator.generators.case_reviewers import generate_case_reviewers
from data_generator.generators.integrity_cases import generate_integrity_cases
from data_generator.generators.integrity_rules import generate_integrity_rules
from data_generator.generators.learners import generate_learners
from data_generator.generators.reviewers import generate_reviewers
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
# Module-scoped fixture — full generation chain, executed once per module
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def generated_data():
    """Generate the full chain up to CaseReviewer with SEED=20261022.

    Chain order:
      IntegrityRule → Learner → Assessment → Reviewer → Submission
      → SimilarityReport → IntegrityCase → CaseReviewer
    """
    rng, nprng, faker = _init_rng()
    rules_df = generate_integrity_rules(rng)
    learners_df = generate_learners(rng, nprng, faker)
    assessments_df = generate_assessments(rng, faker)
    reviewers_df = generate_reviewers(rng, faker)
    submissions_df = generate_submissions(rng, nprng, learners_df, assessments_df)
    reports_df = generate_similarity_reports(nprng, submissions_df, rules_df)
    cases_df = generate_integrity_cases(rng, reports_df)
    case_reviewers_df = generate_case_reviewers(rng, cases_df, reviewers_df)
    return cases_df, reviewers_df, case_reviewers_df


# ---------------------------------------------------------------------------
# Property 9: Every case has a PRIMARY reviewer
# ---------------------------------------------------------------------------


def test_every_case_has_at_least_one_primary_reviewer(generated_data):
    # Feature: academic-integrity-system, Property 9: Every case has a PRIMARY reviewer
    cases_df, _reviewers_df, case_reviewers_df = generated_data

    all_case_ids = set(cases_df["case_id"])
    primary_case_ids = set(
        case_reviewers_df.loc[
            case_reviewers_df["assignment_role"] == "PRIMARY", "case_id"
        ]
    )
    missing = all_case_ids - primary_case_ids

    assert not missing, (
        f"Found {len(missing)} case_id(s) with no PRIMARY reviewer assignment: "
        f"{sorted(missing)[:10]}"  # show up to 10 for brevity
    )


def test_primary_reviewer_case_ids_are_subset_of_integrity_cases(generated_data):
    # Feature: academic-integrity-system, Property 9: Every case has a PRIMARY reviewer
    cases_df, _reviewers_df, case_reviewers_df = generated_data

    all_case_ids = set(cases_df["case_id"])
    primary_df = case_reviewers_df[case_reviewers_df["assignment_role"] == "PRIMARY"]
    orphaned = set(primary_df["case_id"]) - all_case_ids

    assert not orphaned, (
        f"Found {len(orphaned)} PRIMARY CaseReviewer row(s) referencing unknown "
        f"case_id(s): {sorted(orphaned)[:10]}"
    )


def test_every_case_id_has_exactly_one_primary_reviewer(generated_data):
    # Feature: academic-integrity-system, Property 9: Every case has a PRIMARY reviewer
    _cases_df, _reviewers_df, case_reviewers_df = generated_data

    primary_counts = (
        case_reviewers_df[case_reviewers_df["assignment_role"] == "PRIMARY"]
        .groupby("case_id")
        .size()
    )
    multi_primary = primary_counts[primary_counts > 1]

    assert multi_primary.empty, (
        f"Found {len(multi_primary)} case_id(s) with more than one PRIMARY reviewer: "
        f"{multi_primary.index.tolist()[:10]}"
    )


# ---------------------------------------------------------------------------
# Property 10: CONFLICT rows have non-null reason
# ---------------------------------------------------------------------------


def test_conflict_rows_have_non_null_non_empty_conflict_reason(generated_data):
    # Feature: academic-integrity-system, Property 10: CONFLICT rows have non-null reason
    _cases_df, _reviewers_df, case_reviewers_df = generated_data

    conflict_df = case_reviewers_df[case_reviewers_df["conflict_status"] == "CONFLICT"]
    bad_reason_mask = conflict_df["conflict_reason"].isna() | (
        conflict_df["conflict_reason"].astype(str).str.strip() == ""
    )

    assert not bad_reason_mask.any(), (
        f"Found {bad_reason_mask.sum()} CONFLICT row(s) with null or empty "
        f"conflict_reason."
    )


def test_at_least_10_conflict_rows_exist(generated_data):
    # Feature: academic-integrity-system, Property 10: CONFLICT rows have non-null reason
    _cases_df, _reviewers_df, case_reviewers_df = generated_data

    conflict_count = int(
        (case_reviewers_df["conflict_status"] == "CONFLICT").sum()
    )

    assert conflict_count >= 10, (
        f"Expected at least 10 CONFLICT rows, found {conflict_count}."
    )


def test_conflict_rows_have_non_null_unassigned_at(generated_data):
    # Feature: academic-integrity-system, Property 10: CONFLICT rows have non-null reason
    _cases_df, _reviewers_df, case_reviewers_df = generated_data

    conflict_df = case_reviewers_df[case_reviewers_df["conflict_status"] == "CONFLICT"]
    null_unassigned = conflict_df["unassigned_at"].isna()

    assert not null_unassigned.any(), (
        f"Found {null_unassigned.sum()} CONFLICT row(s) with null unassigned_at."
    )


def test_non_conflict_rows_have_null_unassigned_at(generated_data):
    # Feature: academic-integrity-system, Property 10: CONFLICT rows have non-null reason
    _cases_df, _reviewers_df, case_reviewers_df = generated_data

    non_conflict_df = case_reviewers_df[
        case_reviewers_df["conflict_status"] != "CONFLICT"
    ]
    non_null_unassigned = non_conflict_df["unassigned_at"].notna()

    assert not non_null_unassigned.any(), (
        f"Found {non_null_unassigned.sum()} non-CONFLICT row(s) with a non-null "
        f"unassigned_at value."
    )
