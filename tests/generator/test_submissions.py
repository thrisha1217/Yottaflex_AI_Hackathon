"""
Property tests for the Submission data generator.

Validates Property 4: Submission referential integrity.
Every learner_id in the generated Submission DataFrame must exist in the
Learner DataFrame, and every assessment_id must exist in the Assessment
DataFrame.

Feature: academic-integrity-system
"""

import random

import numpy as np
import pytest
from faker import Faker

from data_generator.config import SEED, TARGET_SUBMISSIONS
from data_generator.generators.assessments import generate_assessments
from data_generator.generators.learners import generate_learners
from data_generator.generators.submissions import generate_submissions


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
def generated_data():
    """Generate learners, assessments, and submissions once per module."""
    rng, nprng, faker = _init_rng()
    learners_df = generate_learners(rng, nprng, faker)
    assessments_df = generate_assessments(rng, faker)
    submissions_df = generate_submissions(rng, nprng, learners_df, assessments_df)
    return learners_df, assessments_df, submissions_df


# ---------------------------------------------------------------------------
# Property 4: Submission referential integrity
# ---------------------------------------------------------------------------

def test_submission_learner_ids_are_referentially_intact(generated_data):
    # Feature: academic-integrity-system, Property 4: Submission referential integrity
    learners_df, assessments_df, submissions_df = generated_data

    valid_learner_ids = set(learners_df["learner_id"])
    invalid_rows = ~submissions_df["learner_id"].isin(valid_learner_ids)

    assert not invalid_rows.any(), (
        f"Found {invalid_rows.sum()} submission(s) with learner_id values "
        f"not present in the Learner DataFrame: "
        f"{submissions_df.loc[invalid_rows, 'learner_id'].unique().tolist()}"
    )


def test_submission_assessment_ids_are_referentially_intact(generated_data):
    # Feature: academic-integrity-system, Property 4: Submission referential integrity
    learners_df, assessments_df, submissions_df = generated_data

    valid_assessment_ids = set(assessments_df["assessment_id"])
    invalid_rows = ~submissions_df["assessment_id"].isin(valid_assessment_ids)

    assert not invalid_rows.any(), (
        f"Found {invalid_rows.sum()} submission(s) with assessment_id values "
        f"not present in the Assessment DataFrame: "
        f"{submissions_df.loc[invalid_rows, 'assessment_id'].unique().tolist()}"
    )


def test_submission_row_count_is_exactly_10000(generated_data):
    # Feature: academic-integrity-system, Property 4: Submission referential integrity
    _learners_df, _assessments_df, submissions_df = generated_data

    assert len(submissions_df) == TARGET_SUBMISSIONS, (
        f"Expected exactly {TARGET_SUBMISSIONS} Submission rows, "
        f"got {len(submissions_df)}"
    )
