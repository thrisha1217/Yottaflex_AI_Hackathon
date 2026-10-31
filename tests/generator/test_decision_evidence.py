"""
Tests for the DecisionEvidence data generator.

Validates:

  Requirement 4.7 — DecisionEvidence generation
    Approximately 1,200 rows produced (between 900 and 1,500).
    Composite PK (decision_id, evidence_id) is unique.
    All evidence_id values reference existing EvidenceItem rows.
    All decision_id values reference existing Decision rows.
    Each decision is linked to at least one evidence item.
    Every evidence_id for a decision belongs to the same case.

Feature: academic-integrity-system
"""

import random

import numpy as np
import pytest
from faker import Faker

from data_generator.config import SEED
from data_generator.generators.assessments import generate_assessments
from data_generator.generators.decisions import generate_decisions
from data_generator.generators.decision_evidence import generate_decision_evidence
from data_generator.generators.evidence_items import generate_evidence_items
from data_generator.generators.integrity_cases import generate_integrity_cases
from data_generator.generators.integrity_rules import generate_integrity_rules
from data_generator.generators.learners import generate_learners
from data_generator.generators.reviewers import generate_reviewers
from data_generator.generators.similarity_reports import generate_similarity_reports
from data_generator.generators.submissions import generate_submissions


def _init_rng():
    """Initialise all RNG sources with the fixed project seed."""
    rng   = random.Random(SEED)
    nprng = np.random.default_rng(SEED)
    faker = Faker()
    Faker.seed(SEED)
    return rng, nprng, faker


# ---------------------------------------------------------------------------
# Module-scoped fixture — full generation chain, executed once per module
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def generated_data():
    """Generate the full chain up through decision_evidence with SEED=20261022."""
    rng, nprng, faker = _init_rng()
    rules_df           = generate_integrity_rules(rng)
    learners_df        = generate_learners(rng, nprng, faker)
    assessments_df     = generate_assessments(rng, faker)
    submissions_df     = generate_submissions(rng, nprng, learners_df, assessments_df)
    reports_df         = generate_similarity_reports(nprng, submissions_df, rules_df)
    cases_df           = generate_integrity_cases(rng, reports_df)
    reviewers_df       = generate_reviewers(rng, faker)
    decisions_df       = generate_decisions(rng, faker, cases_df, reviewers_df)
    evidence_df        = generate_evidence_items(rng, faker, cases_df)
    decision_evidence_df = generate_decision_evidence(rng, decisions_df, evidence_df)
    return decisions_df, evidence_df, decision_evidence_df


# ---------------------------------------------------------------------------
# Row count
# ---------------------------------------------------------------------------


def test_row_count_within_expected_range(generated_data):
    # Validates: Requirements 4.7
    _decisions_df, _evidence_df, de_df = generated_data

    assert 900 <= len(de_df) <= 1500, (
        f"Expected between 900 and 1500 DecisionEvidence rows, got {len(de_df)}"
    )


# ---------------------------------------------------------------------------
# Composite PK uniqueness
# ---------------------------------------------------------------------------


def test_composite_pk_is_unique(generated_data):
    # Validates: Requirements 4.7
    _decisions_df, _evidence_df, de_df = generated_data

    duplicates = de_df.duplicated(subset=["decision_id", "evidence_id"])
    assert not duplicates.any(), (
        f"Found {duplicates.sum()} duplicate (decision_id, evidence_id) pair(s)."
    )


# ---------------------------------------------------------------------------
# FK integrity — evidence_id
# ---------------------------------------------------------------------------


def test_all_evidence_ids_exist_in_evidence_df(generated_data):
    # Validates: Requirements 4.7
    _decisions_df, evidence_df, de_df = generated_data

    valid_ids    = set(evidence_df["evidence_id"])
    invalid_mask = ~de_df["evidence_id"].isin(valid_ids)
    assert not invalid_mask.any(), (
        f"Found {invalid_mask.sum()} row(s) with evidence_id not in evidence_df."
    )


# ---------------------------------------------------------------------------
# FK integrity — decision_id
# ---------------------------------------------------------------------------


def test_all_decision_ids_exist_in_decisions_df(generated_data):
    # Validates: Requirements 4.7
    decisions_df, _evidence_df, de_df = generated_data

    valid_ids    = set(decisions_df["decision_id"])
    invalid_mask = ~de_df["decision_id"].isin(valid_ids)
    assert not invalid_mask.any(), (
        f"Found {invalid_mask.sum()} row(s) with decision_id not in decisions_df."
    )


# ---------------------------------------------------------------------------
# Each decision has at least one linked evidence item
# ---------------------------------------------------------------------------


def test_every_decision_has_at_least_one_evidence_item(generated_data):
    # Validates: Requirements 4.7
    decisions_df, _evidence_df, de_df = generated_data

    linked_decisions = set(de_df["decision_id"].unique())
    all_decisions    = set(decisions_df["decision_id"].unique())
    missing          = all_decisions - linked_decisions
    assert not missing, (
        f"{len(missing)} decision(s) have no linked evidence items: "
        f"{sorted(missing)[:10]}{'...' if len(missing) > 10 else ''}"
    )


# ---------------------------------------------------------------------------
# Each decision links between 1 and 5 evidence items
# ---------------------------------------------------------------------------


def test_evidence_items_per_decision_within_bounds(generated_data):
    # Validates: Requirements 4.7
    _decisions_df, _evidence_df, de_df = generated_data

    counts = de_df.groupby("decision_id")["evidence_id"].count()
    over   = counts[counts > 5]
    assert over.empty, (
        f"{len(over)} decision(s) are linked to more than 5 evidence items: "
        f"{over.to_dict()}"
    )


# ---------------------------------------------------------------------------
# Evidence items for each decision belong to the same case as the decision
# ---------------------------------------------------------------------------


def test_evidence_items_belong_to_same_case_as_decision(generated_data):
    # Validates: Requirements 4.7
    decisions_df, evidence_df, de_df = generated_data

    # Build lookup maps
    decision_case = decisions_df.set_index("decision_id")["case_id"].to_dict()
    evidence_case = evidence_df.set_index("evidence_id")["case_id"].to_dict()

    mismatches = [
        (row["decision_id"], row["evidence_id"])
        for _, row in de_df.iterrows()
        if decision_case.get(row["decision_id"]) != evidence_case.get(row["evidence_id"])
    ]

    assert not mismatches, (
        f"Found {len(mismatches)} (decision_id, evidence_id) pair(s) where the "
        f"evidence belongs to a different case than the decision. "
        f"First few: {mismatches[:5]}"
    )
