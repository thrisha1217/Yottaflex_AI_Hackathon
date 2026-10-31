"""
Property tests for the IntegrityCase data generator.

Validates:

  Property 8: Cases link to flagged reports only
    Every report_id in the IntegrityCase DataFrame corresponds to a
    SimilarityReport row where review_required = TRUE.
    Exactly 300 IntegrityCase rows are generated.

Feature: academic-integrity-system
"""

import random

import numpy as np
import pytest
from faker import Faker

from data_generator.config import SEED, TARGET_CASES
from data_generator.generators.assessments import generate_assessments
from data_generator.generators.integrity_cases import generate_integrity_cases
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
# Module-scoped fixture — full generation chain, executed once per module
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def generated_data():
    """Generate the full chain: rules → learners → assessments → submissions
    → similarity_reports → integrity_cases with SEED=20261022."""
    rng, nprng, faker = _init_rng()
    rules_df = generate_integrity_rules(rng)
    learners_df = generate_learners(rng, nprng, faker)
    assessments_df = generate_assessments(rng, faker)
    submissions_df = generate_submissions(rng, nprng, learners_df, assessments_df)
    reports_df = generate_similarity_reports(nprng, submissions_df, rules_df)
    cases_df = generate_integrity_cases(rng, reports_df)
    return reports_df, cases_df


# ---------------------------------------------------------------------------
# Property 8: Cases link to flagged reports only
# ---------------------------------------------------------------------------


def test_integrity_case_row_count_is_exactly_300(generated_data):
    # Feature: academic-integrity-system, Property 8: Cases link to flagged reports only
    _reports_df, cases_df = generated_data

    assert len(cases_df) == TARGET_CASES, (
        f"Expected exactly {TARGET_CASES} IntegrityCase rows, got {len(cases_df)}"
    )


def test_every_case_report_id_references_a_flagged_report(generated_data):
    # Feature: academic-integrity-system, Property 8: Cases link to flagged reports only
    reports_df, cases_df = generated_data

    flagged_report_ids = set(
        reports_df.loc[reports_df["review_required"] == True, "report_id"]
    )
    unflagged_mask = ~cases_df["report_id"].isin(flagged_report_ids)

    assert not unflagged_mask.any(), (
        f"Found {unflagged_mask.sum()} IntegrityCase row(s) whose report_id "
        f"does not correspond to a flagged (review_required=TRUE) SimilarityReport: "
        f"{cases_df.loc[unflagged_mask, 'report_id'].tolist()}"
    )


def test_every_case_report_id_exists_in_similarity_reports(generated_data):
    # Feature: academic-integrity-system, Property 8: Cases link to flagged reports only
    reports_df, cases_df = generated_data

    all_report_ids = set(reports_df["report_id"])
    orphaned_mask = ~cases_df["report_id"].isin(all_report_ids)

    assert not orphaned_mask.any(), (
        f"Found {orphaned_mask.sum()} IntegrityCase row(s) whose report_id "
        f"does not exist in the SimilarityReport DataFrame at all: "
        f"{cases_df.loc[orphaned_mask, 'report_id'].tolist()}"
    )


def test_case_report_ids_are_unique(generated_data):
    # Feature: academic-integrity-system, Property 8: Cases link to flagged reports only
    _reports_df, cases_df = generated_data

    duplicates = cases_df["report_id"].duplicated(keep=False)
    assert not duplicates.any(), (
        f"Found {duplicates.sum()} IntegrityCase row(s) with duplicate report_id "
        f"(each flagged report may only be linked to one case): "
        f"{cases_df.loc[duplicates, 'report_id'].tolist()}"
    )


def test_flagged_reports_outnumber_cases(generated_data):
    # Feature: academic-integrity-system, Property 8: Cases link to flagged reports only
    reports_df, cases_df = generated_data

    flagged_count = int(reports_df["review_required"].sum())
    assert flagged_count >= TARGET_CASES, (
        f"Not enough flagged SimilarityReport rows to populate {TARGET_CASES} "
        f"cases: only {flagged_count} flagged reports exist."
    )
