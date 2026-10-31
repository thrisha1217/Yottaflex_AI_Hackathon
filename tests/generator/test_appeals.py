"""
Property tests for the Appeal data generator.

Validates:

  Property 13: Appeals link to cases with decisions
    Every case_id in the Appeal DataFrame has at least one row in the
    Decision DataFrame.

  Additional checks:
    ~90 rows generated (between 80 and 100)
    All five appeal_status values are represented
    resolved_at is non-null for UPHELD/OVERTURNED, null for others

Feature: academic-integrity-system
"""

import random

import numpy as np
import pytest
from faker import Faker

from data_generator.config import SEED
from data_generator.generators.appeals import generate_appeals
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
    """Generate the full chain up through appeals with SEED=20261022."""
    rng, nprng, faker = _init_rng()
    rules_df       = generate_integrity_rules(rng)
    learners_df    = generate_learners(rng, nprng, faker)
    assessments_df = generate_assessments(rng, faker)
    reviewers_df   = generate_reviewers(rng, faker)
    submissions_df = generate_submissions(rng, nprng, learners_df, assessments_df)
    reports_df     = generate_similarity_reports(nprng, submissions_df, rules_df)
    cases_df       = generate_integrity_cases(rng, reports_df)
    decisions_df   = generate_decisions(rng, faker, cases_df, reviewers_df)
    appeals_df     = generate_appeals(rng, faker, cases_df, decisions_df, learners_df)
    return cases_df, decisions_df, learners_df, appeals_df


# ---------------------------------------------------------------------------
# Property 13: Appeals link to cases with decisions
# ---------------------------------------------------------------------------


def test_every_appeal_case_id_has_a_decision(generated_data):
    # Feature: academic-integrity-system, Property 13: Appeals link to cases with decisions
    _cases_df, decisions_df, _learners_df, appeals_df = generated_data

    decided_case_ids = set(decisions_df["case_id"])
    orphaned_mask = ~appeals_df["case_id"].isin(decided_case_ids)

    assert not orphaned_mask.any(), (
        f"Found {orphaned_mask.sum()} Appeal row(s) whose case_id has no "
        f"corresponding Decision row: "
        f"{appeals_df.loc[orphaned_mask, 'case_id'].tolist()}"
    )


# ---------------------------------------------------------------------------
# Row count: approximately 90 (80–100)
# ---------------------------------------------------------------------------


def test_appeal_row_count_is_approximately_90(generated_data):
    # Feature: academic-integrity-system, Property 13: Appeals link to cases with decisions
    _cases_df, _decisions_df, _learners_df, appeals_df = generated_data

    assert 80 <= len(appeals_df) <= 100, (
        f"Expected approximately 90 Appeal rows (80–100), got {len(appeals_df)}"
    )


# ---------------------------------------------------------------------------
# All five appeal_status values are represented
# ---------------------------------------------------------------------------


_ALL_APPEAL_STATUSES = {"SUBMITTED", "UNDER_REVIEW", "UPHELD", "OVERTURNED", "REMANDED"}


def test_all_five_appeal_statuses_are_represented(generated_data):
    # Feature: academic-integrity-system, Property 13: Appeals link to cases with decisions
    _cases_df, _decisions_df, _learners_df, appeals_df = generated_data

    present = set(appeals_df["appeal_status"].unique())
    missing = _ALL_APPEAL_STATUSES - present

    assert not missing, (
        f"Not all five appeal_status values are represented; missing: {missing}"
    )


def test_appeal_status_values_are_valid_enum_members(generated_data):
    # Feature: academic-integrity-system, Property 13: Appeals link to cases with decisions
    _cases_df, _decisions_df, _learners_df, appeals_df = generated_data

    invalid_mask = ~appeals_df["appeal_status"].isin(_ALL_APPEAL_STATUSES)
    assert not invalid_mask.any(), (
        f"Found invalid appeal_status values: "
        f"{appeals_df.loc[invalid_mask, 'appeal_status'].unique().tolist()}"
    )


# ---------------------------------------------------------------------------
# resolved_at: non-null for UPHELD/OVERTURNED, null for others
# ---------------------------------------------------------------------------

_RESOLVED_STATUSES = {"UPHELD", "OVERTURNED"}
_UNRESOLVED_STATUSES = _ALL_APPEAL_STATUSES - _RESOLVED_STATUSES


def test_resolved_at_is_non_null_for_upheld_and_overturned(generated_data):
    # Feature: academic-integrity-system, Property 13: Appeals link to cases with decisions
    _cases_df, _decisions_df, _learners_df, appeals_df = generated_data

    resolved_mask = appeals_df["appeal_status"].isin(_RESOLVED_STATUSES)
    missing_resolved_at = appeals_df.loc[resolved_mask, "resolved_at"].isna()

    assert not missing_resolved_at.any(), (
        f"Found {missing_resolved_at.sum()} UPHELD/OVERTURNED Appeal row(s) "
        f"where resolved_at is NULL."
    )


def test_resolved_at_is_null_for_non_resolved_statuses(generated_data):
    # Feature: academic-integrity-system, Property 13: Appeals link to cases with decisions
    _cases_df, _decisions_df, _learners_df, appeals_df = generated_data

    unresolved_mask = appeals_df["appeal_status"].isin(_UNRESOLVED_STATUSES)
    unexpected_resolved_at = appeals_df.loc[unresolved_mask, "resolved_at"].notna()

    assert not unexpected_resolved_at.any(), (
        f"Found {unexpected_resolved_at.sum()} Appeal row(s) with status in "
        f"{_UNRESOLVED_STATUSES} but non-null resolved_at."
    )
