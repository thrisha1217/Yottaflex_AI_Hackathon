"""
Property test for Generator reproducibility.

# Feature: academic-integrity-system, Property 1: Generator reproducibility

Validates that running the full generator pipeline twice from the same
seed produces byte-identical DataFrames for every table.

**Validates: Requirements 1.2**
"""

import random

import numpy as np
import pandas as pd
import pytest
from faker import Faker

from data_generator.config import SEED
from data_generator.generators.integrity_rules import generate_integrity_rules
from data_generator.generators.learners import generate_learners
from data_generator.generators.assessments import generate_assessments
from data_generator.generators.reviewers import generate_reviewers
from data_generator.generators.submissions import generate_submissions
from data_generator.generators.similarity_reports import generate_similarity_reports
from data_generator.generators.integrity_cases import generate_integrity_cases
from data_generator.generators.case_reviewers import generate_case_reviewers
from data_generator.generators.evidence_items import generate_evidence_items
from data_generator.generators.decisions import generate_decisions
from data_generator.generators.decision_evidence import generate_decision_evidence
from data_generator.generators.appeals import generate_appeals
from data_generator.generators.appeal_reviews import generate_appeal_reviews
from data_generator.generators.case_events import generate_case_events


def _init_rng():
    """Initialise all three RNG sources from the fixed seed."""
    rng = random.Random(SEED)
    nprng = np.random.default_rng(SEED)
    faker = Faker()
    Faker.seed(SEED)
    return rng, nprng, faker


def _run_pipeline():
    """Execute the full generator chain and return a dict of {name: DataFrame}."""
    rng, nprng, faker = _init_rng()

    rules_df = generate_integrity_rules(rng)
    learners_df = generate_learners(rng, nprng, faker)
    assessments_df = generate_assessments(rng, faker)
    reviewers_df = generate_reviewers(rng, faker)
    submissions_df = generate_submissions(rng, nprng, learners_df, assessments_df)
    reports_df = generate_similarity_reports(nprng, submissions_df, rules_df)
    cases_df = generate_integrity_cases(rng, reports_df)
    case_reviewers_df = generate_case_reviewers(rng, cases_df, reviewers_df)
    evidence_df = generate_evidence_items(rng, faker, cases_df)
    decisions_df = generate_decisions(rng, faker, cases_df, reviewers_df)
    decision_evidence_df = generate_decision_evidence(rng, decisions_df, evidence_df)
    appeals_df = generate_appeals(rng, faker, cases_df, decisions_df, learners_df)
    appeal_reviews_df = generate_appeal_reviews(
        rng, faker, appeals_df, case_reviewers_df, reviewers_df
    )
    events_df = generate_case_events(rng, cases_df, appeals_df)

    return {
        "integrity_rules": rules_df,
        "learners": learners_df,
        "assessments": assessments_df,
        "reviewers": reviewers_df,
        "submissions": submissions_df,
        "similarity_reports": reports_df,
        "integrity_cases": cases_df,
        "case_reviewers": case_reviewers_df,
        "evidence_items": evidence_df,
        "decisions": decisions_df,
        "decision_evidence": decision_evidence_df,
        "appeals": appeals_df,
        "appeal_reviews": appeal_reviews_df,
        "case_events": events_df,
    }


# ---------------------------------------------------------------------------
# Fixtures — run the pipeline twice, independently, at module scope so the
# cost is paid once per test session.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def run_one():
    return _run_pipeline()


@pytest.fixture(scope="module")
def run_two():
    return _run_pipeline()


# ---------------------------------------------------------------------------
# Property 1: Generator reproducibility
# ---------------------------------------------------------------------------

TABLE_NAMES = [
    "integrity_rules",
    "learners",
    "assessments",
    "reviewers",
    "submissions",
    "similarity_reports",
    "integrity_cases",
    "case_reviewers",
    "evidence_items",
    "decisions",
    "decision_evidence",
    "appeals",
    "appeal_reviews",
    "case_events",
]


@pytest.mark.parametrize("table_name", TABLE_NAMES)
def test_all_tables_are_identical_across_two_runs(run_one, run_two, table_name):
    """
    # Feature: academic-integrity-system, Property 1: Generator reproducibility

    Running the generator twice from SEED=20261022 must produce DataFrames
    that are byte-identical when serialised to CSV — i.e. every cell value,
    column name, and row order must match exactly.

    **Validates: Requirements 1.2**
    """
    df_a = run_one[table_name]
    df_b = run_two[table_name]

    # Shape must match before we can compare cell-by-cell
    assert df_a.shape == df_b.shape, (
        f"[{table_name}] Shape mismatch between run 1 {df_a.shape} "
        f"and run 2 {df_b.shape}"
    )

    # Column names and order must be identical
    assert list(df_a.columns) == list(df_b.columns), (
        f"[{table_name}] Column order/names differ between runs: "
        f"{list(df_a.columns)} vs {list(df_b.columns)}"
    )

    # Cell-by-cell exact equality (check_exact=True, no dtype coercion)
    pd.testing.assert_frame_equal(
        df_a.reset_index(drop=True),
        df_b.reset_index(drop=True),
        check_exact=True,
        check_like=False,  # preserve column/row order
        obj=f"table '{table_name}'",
    )
