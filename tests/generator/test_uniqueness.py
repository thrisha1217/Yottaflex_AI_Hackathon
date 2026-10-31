"""
Property tests for email uniqueness across participant generators.

Validates Property 3: Email uniqueness for both Learner and Reviewer
DataFrames — no duplicate emails within each table.

Feature: academic-integrity-system
"""

import random

import numpy as np
import pytest
from faker import Faker

from data_generator.config import SEED
from data_generator.generators.learners import generate_learners
from data_generator.generators.reviewers import generate_reviewers


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
def participant_data():
    """Generate Learner and Reviewer DataFrames once per module."""
    rng, nprng, faker = _init_rng()
    learners_df = generate_learners(rng, nprng, faker)
    reviewers_df = generate_reviewers(rng, faker)
    return learners_df, reviewers_df


# ---------------------------------------------------------------------------
# Property 3: Email uniqueness — Learner
# ---------------------------------------------------------------------------


def test_learner_email_uniqueness(participant_data):
    # Feature: academic-integrity-system, Property 3: Email uniqueness
    learners_df, _ = participant_data
    duplicate_mask = learners_df["email"].duplicated(keep=False)

    assert not duplicate_mask.any(), (
        f"Found {duplicate_mask.sum()} Learner row(s) with duplicate emails: "
        f"{learners_df.loc[duplicate_mask, ['learner_id', 'email']].to_dict('records')}"
    )


# ---------------------------------------------------------------------------
# Property 3: Email uniqueness — Reviewer (stub for task 2.6)
# ---------------------------------------------------------------------------


def test_reviewer_email_uniqueness(participant_data):
    # Feature: academic-integrity-system, Property 3: Email uniqueness
    _, reviewers_df = participant_data
    duplicate_mask = reviewers_df["email"].duplicated(keep=False)

    assert not duplicate_mask.any(), (
        f"Found {duplicate_mask.sum()} Reviewer row(s) with duplicate emails: "
        f"{reviewers_df.loc[duplicate_mask, ['reviewer_id', 'email']].to_dict('records')}"
    )
