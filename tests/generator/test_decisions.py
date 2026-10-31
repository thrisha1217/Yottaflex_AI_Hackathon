"""
Property tests for the Decision data generator.

Validates:

  Requirement 4.6 — Decision generation
    Exactly 300 Decision rows are generated, one per IntegrityCase.
    Outcomes are distributed across NO_VIOLATION, VIOLATION, INCONCLUSIVE.
    decided_at is strictly after the corresponding case's opened_at.
    reviewer_id references an active reviewer.
    is_final is True for all rows.
    previous_decision_id is None for all rows.

Feature: academic-integrity-system
"""

import random

import numpy as np
import pytest
from faker import Faker

from data_generator.config import SEED, TARGET_DECISIONS
from data_generator.generators.assessments import generate_assessments
from data_generator.generators.decisions import generate_decisions
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
    """Generate the full chain up through decisions with SEED=20261022."""
    rng, nprng, faker = _init_rng()
    rules_df       = generate_integrity_rules(rng)
    learners_df    = generate_learners(rng, nprng, faker)
    assessments_df = generate_assessments(rng, faker)
    submissions_df = generate_submissions(rng, nprng, learners_df, assessments_df)
    reports_df     = generate_similarity_reports(nprng, submissions_df, rules_df)
    cases_df       = generate_integrity_cases(rng, reports_df)
    reviewers_df   = generate_reviewers(rng, faker)
    decisions_df   = generate_decisions(rng, faker, cases_df, reviewers_df)
    return cases_df, reviewers_df, decisions_df


# ---------------------------------------------------------------------------
# Row count
# ---------------------------------------------------------------------------


def test_decision_row_count_is_exactly_300(generated_data):
    # Validates: Requirements 4.6
    _cases_df, _reviewers_df, decisions_df = generated_data

    assert len(decisions_df) == TARGET_DECISIONS, (
        f"Expected exactly {TARGET_DECISIONS} Decision rows, got {len(decisions_df)}"
    )


# ---------------------------------------------------------------------------
# One decision per case
# ---------------------------------------------------------------------------


def test_one_decision_per_case(generated_data):
    # Validates: Requirements 4.6
    _cases_df, _reviewers_df, decisions_df = generated_data

    duplicates = decisions_df["case_id"].duplicated(keep=False)
    assert not duplicates.any(), (
        f"Found {duplicates.sum()} Decision row(s) with duplicate case_id "
        f"(each IntegrityCase may only have one Decision): "
        f"{decisions_df.loc[duplicates, 'case_id'].tolist()}"
    )


# ---------------------------------------------------------------------------
# Valid decision_outcome values
# ---------------------------------------------------------------------------


_VALID_OUTCOMES = {"NO_VIOLATION", "VIOLATION", "INCONCLUSIVE"}


def test_decision_outcomes_are_valid_enum_values(generated_data):
    # Validates: Requirements 4.6
    _cases_df, _reviewers_df, decisions_df = generated_data

    invalid_mask = ~decisions_df["decision_outcome"].isin(_VALID_OUTCOMES)
    assert not invalid_mask.any(), (
        f"Found invalid decision_outcome values: "
        f"{decisions_df.loc[invalid_mask, 'decision_outcome'].unique().tolist()}"
    )


def test_all_three_outcomes_are_represented(generated_data):
    # Validates: Requirements 4.6
    _cases_df, _reviewers_df, decisions_df = generated_data

    present = set(decisions_df["decision_outcome"].unique())
    missing = _VALID_OUTCOMES - present
    assert not missing, (
        f"Not all decision_outcome values are represented; missing: {missing}"
    )


# ---------------------------------------------------------------------------
# decided_at > opened_at
# ---------------------------------------------------------------------------


def test_decided_at_is_after_opened_at(generated_data):
    # Validates: Requirements 4.6
    cases_df, _reviewers_df, decisions_df = generated_data

    import pandas as pd

    merged = decisions_df.merge(
        cases_df[["case_id", "opened_at"]],
        on="case_id",
        how="left",
    )
    decided_arr = pd.to_datetime(merged["decided_at"])
    opened_arr  = pd.to_datetime(merged["opened_at"])

    bad_mask = decided_arr <= opened_arr
    assert not bad_mask.any(), (
        f"Found {bad_mask.sum()} Decision row(s) where decided_at is not "
        f"strictly after opened_at."
    )


# ---------------------------------------------------------------------------
# reviewer_id references an active reviewer
# ---------------------------------------------------------------------------


def test_reviewer_id_references_active_reviewer(generated_data):
    # Validates: Requirements 4.6
    _cases_df, reviewers_df, decisions_df = generated_data

    active_ids = set(reviewers_df.loc[reviewers_df["status"] == "ACTIVE", "reviewer_id"])
    invalid_mask = ~decisions_df["reviewer_id"].isin(active_ids)

    assert not invalid_mask.any(), (
        f"Found {invalid_mask.sum()} Decision row(s) with reviewer_id not "
        f"referencing an active reviewer."
    )


# ---------------------------------------------------------------------------
# is_final = True for all rows
# ---------------------------------------------------------------------------


def test_is_final_is_true_for_all_rows(generated_data):
    # Validates: Requirements 4.6
    _cases_df, _reviewers_df, decisions_df = generated_data

    not_final = ~decisions_df["is_final"]
    assert not not_final.any(), (
        f"Found {not_final.sum()} Decision row(s) where is_final is not True."
    )


# ---------------------------------------------------------------------------
# previous_decision_id = None for all rows
# ---------------------------------------------------------------------------


def test_previous_decision_id_is_none_for_all_rows(generated_data):
    # Validates: Requirements 4.6
    _cases_df, _reviewers_df, decisions_df = generated_data

    has_prev = decisions_df["previous_decision_id"].notna()
    assert not has_prev.any(), (
        f"Found {has_prev.sum()} Decision row(s) where previous_decision_id "
        f"is not None (API handles revisions via new rows)."
    )


# ---------------------------------------------------------------------------
# decision_id is sequential starting at 1
# ---------------------------------------------------------------------------


def test_decision_id_is_sequential_from_one(generated_data):
    # Validates: Requirements 4.6
    _cases_df, _reviewers_df, decisions_df = generated_data

    expected = list(range(1, TARGET_DECISIONS + 1))
    actual   = decisions_df["decision_id"].tolist()
    assert actual == expected, (
        f"decision_id must be sequential integers starting at 1; "
        f"first mismatch at index {next(i for i, (a, b) in enumerate(zip(actual, expected)) if a != b)}"
    )
