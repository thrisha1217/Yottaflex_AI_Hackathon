"""
Property tests for the Learner data generator.

Validates:
  - Property 2: Year of study range — year_of_study is in 1–10 inclusive
    for all 500 Learner rows.
  - Property 3: Email uniqueness — no duplicate emails within the Learner
    DataFrame.

Feature: academic-integrity-system
"""

import random

import numpy as np
import pytest
from faker import Faker

from data_generator.config import SEED, TARGET_LEARNERS
from data_generator.generators.learners import generate_learners


def _init_rng():
    """Initialise all RNG sources with the fixed project seed."""
    rng = random.Random(SEED)
    nprng = np.random.default_rng(SEED)
    faker = Faker()
    Faker.seed(SEED)
    return rng, nprng, faker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def learners_df():
    """Generate the Learner DataFrame once per module."""
    rng, nprng, faker = _init_rng()
    return generate_learners(rng, nprng, faker)


# ---------------------------------------------------------------------------
# Property 2: Year of study range
# ---------------------------------------------------------------------------


def test_year_of_study_within_valid_range(learners_df):
    # Feature: academic-integrity-system, Property 2: Year of study range
    out_of_range = ~learners_df["year_of_study"].between(1, 10)

    assert not out_of_range.any(), (
        f"Found {out_of_range.sum()} row(s) with year_of_study outside 1–10: "
        f"{learners_df.loc[out_of_range, ['learner_id', 'year_of_study']].to_dict('records')}"
    )


def test_year_of_study_row_count_is_exactly_500(learners_df):
    # Feature: academic-integrity-system, Property 2: Year of study range
    assert len(learners_df) == TARGET_LEARNERS, (
        f"Expected exactly {TARGET_LEARNERS} Learner rows, got {len(learners_df)}"
    )


def test_year_of_study_values_are_integers(learners_df):
    # Feature: academic-integrity-system, Property 2: Year of study range
    non_int = learners_df["year_of_study"].apply(lambda v: not isinstance(v, (int,)))

    assert not non_int.any(), (
        f"Found {non_int.sum()} row(s) where year_of_study is not an integer."
    )


# ---------------------------------------------------------------------------
# Property 3: Email uniqueness (Learner)
# ---------------------------------------------------------------------------


def test_learner_emails_are_unique(learners_df):
    # Feature: academic-integrity-system, Property 3: Email uniqueness
    duplicate_mask = learners_df["email"].duplicated(keep=False)

    assert not duplicate_mask.any(), (
        f"Found {duplicate_mask.sum()} row(s) with duplicate email addresses: "
        f"{learners_df.loc[duplicate_mask, ['learner_id', 'email']].to_dict('records')}"
    )


def test_learner_email_count_matches_row_count(learners_df):
    # Feature: academic-integrity-system, Property 3: Email uniqueness
    assert learners_df["email"].nunique() == len(learners_df), (
        f"Unique email count ({learners_df['email'].nunique()}) does not match "
        f"total row count ({len(learners_df)})"
    )
