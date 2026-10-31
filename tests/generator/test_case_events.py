"""
Property tests for the CaseEvent data generator.

Validates:

  Property 16: Required CaseEvent types per case
    Every case_id has at least one CASE_CREATED event and at least one
    DECISION_RECORDED event.

  Property 17: APPEAL_SUBMITTED after DECISION_RECORDED
    For every case with an APPEAL_SUBMITTED event, its occurred_at is
    strictly after the case's DECISION_RECORDED.occurred_at.

  Property 18: CaseEvent timestamps non-decreasing per case
    No event within a case is timestamped earlier than its predecessor
    (strict ascending by event_id order).

  Additional checks:
    Total rows >= 3,000
    APPEAL_SUBMITTED events only appear for cases in appeals_df

Feature: academic-integrity-system
"""

import random

import numpy as np
import pytest
from faker import Faker

from data_generator.config import SEED, TARGET_EVENTS
from data_generator.generators.appeals import generate_appeals
from data_generator.generators.assessments import generate_assessments
from data_generator.generators.case_events import generate_case_events
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
    """Generate the full chain up through case_events with SEED=20261022."""
    rng, nprng, faker = _init_rng()
    rules_df        = generate_integrity_rules(rng)
    learners_df     = generate_learners(rng, nprng, faker)
    assessments_df  = generate_assessments(rng, faker)
    reviewers_df    = generate_reviewers(rng, faker)
    submissions_df  = generate_submissions(rng, nprng, learners_df, assessments_df)
    reports_df      = generate_similarity_reports(nprng, submissions_df, rules_df)
    cases_df        = generate_integrity_cases(rng, reports_df)
    decisions_df    = generate_decisions(rng, faker, cases_df, reviewers_df)
    appeals_df      = generate_appeals(rng, faker, cases_df, decisions_df, learners_df)
    events_df       = generate_case_events(rng, cases_df, appeals_df)
    return cases_df, appeals_df, events_df


# ---------------------------------------------------------------------------
# Row count: at least 3,000
# ---------------------------------------------------------------------------


def test_total_event_row_count_is_at_least_3000(generated_data):
    # Feature: academic-integrity-system, Property 16: Required CaseEvent types per case
    _cases_df, _appeals_df, events_df = generated_data

    assert len(events_df) >= TARGET_EVENTS, (
        f"Expected at least {TARGET_EVENTS} CaseEvent rows, got {len(events_df)}"
    )


# ---------------------------------------------------------------------------
# Property 16: Required CaseEvent types per case
# ---------------------------------------------------------------------------


def test_every_case_has_a_case_created_event(generated_data):
    # Feature: academic-integrity-system, Property 16: Required CaseEvent types per case
    cases_df, _appeals_df, events_df = generated_data

    all_case_ids = set(cases_df["case_id"])
    case_created_ids = set(
        events_df.loc[events_df["event_type"] == "CASE_CREATED", "case_id"]
    )
    missing = all_case_ids - case_created_ids

    assert not missing, (
        f"Found {len(missing)} case(s) with no CASE_CREATED event: {missing}"
    )


def test_every_case_has_a_decision_recorded_event(generated_data):
    # Feature: academic-integrity-system, Property 16: Required CaseEvent types per case
    cases_df, _appeals_df, events_df = generated_data

    all_case_ids = set(cases_df["case_id"])
    decision_recorded_ids = set(
        events_df.loc[events_df["event_type"] == "DECISION_RECORDED", "case_id"]
    )
    missing = all_case_ids - decision_recorded_ids

    assert not missing, (
        f"Found {len(missing)} case(s) with no DECISION_RECORDED event: {missing}"
    )


# ---------------------------------------------------------------------------
# Property 17: APPEAL_SUBMITTED after DECISION_RECORDED
# ---------------------------------------------------------------------------


def test_appeal_submitted_occurs_after_decision_recorded(generated_data):
    # Feature: academic-integrity-system, Property 17: APPEAL_SUBMITTED after DECISION_RECORDED
    _cases_df, _appeals_df, events_df = generated_data

    appeal_rows = events_df.loc[events_df["event_type"] == "APPEAL_SUBMITTED"]

    # If no appeal events exist there is nothing to check
    if appeal_rows.empty:
        pytest.skip("No APPEAL_SUBMITTED events found; skipping ordering check.")

    decision_times = (
        events_df.loc[events_df["event_type"] == "DECISION_RECORDED"]
        .set_index("case_id")["occurred_at"]
    )

    violations = []
    for _, appeal_row in appeal_rows.iterrows():
        cid = appeal_row["case_id"]
        t_appeal = appeal_row["occurred_at"]

        assert cid in decision_times.index, (
            f"APPEAL_SUBMITTED exists for case {cid} but no DECISION_RECORDED found"
        )

        t_decision = decision_times[cid]
        if not (t_appeal > t_decision):
            violations.append(
                f"case {cid}: APPEAL_SUBMITTED at {t_appeal} is NOT after "
                f"DECISION_RECORDED at {t_decision}"
            )

    assert not violations, (
        f"Found {len(violations)} APPEAL_SUBMITTED / DECISION_RECORDED ordering "
        f"violation(s):\n" + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# Property 18: CaseEvent timestamps non-decreasing per case
# ---------------------------------------------------------------------------


def test_event_timestamps_are_non_decreasing_within_each_case(generated_data):
    # Feature: academic-integrity-system, Property 18: CaseEvent timestamps non-decreasing per case
    _cases_df, _appeals_df, events_df = generated_data

    violations = []
    for case_id, group in events_df.groupby("case_id", sort=False):
        ordered = group.sort_values("event_id")
        timestamps = ordered["occurred_at"].tolist()

        for i in range(1, len(timestamps)):
            t_prev = timestamps[i - 1]
            t_curr = timestamps[i]
            if not (t_curr >= t_prev):
                violations.append(
                    f"case {case_id}: event at index {i} has occurred_at={t_curr} "
                    f"which is before predecessor occurred_at={t_prev}"
                )

    assert not violations, (
        f"Found {len(violations)} timestamp ordering violation(s) across cases:\n"
        + "\n".join(violations[:20])  # cap output for readability
    )


# ---------------------------------------------------------------------------
# APPEAL_SUBMITTED events only appear for cases present in appeals_df
# ---------------------------------------------------------------------------


def test_appeal_submitted_events_only_for_cases_in_appeals_df(generated_data):
    # Feature: academic-integrity-system, Property 17: APPEAL_SUBMITTED after DECISION_RECORDED
    _cases_df, appeals_df, events_df = generated_data

    appeal_case_ids = set(appeals_df["case_id"])
    appeal_event_case_ids = set(
        events_df.loc[events_df["event_type"] == "APPEAL_SUBMITTED", "case_id"]
    )
    unexpected = appeal_event_case_ids - appeal_case_ids

    assert not unexpected, (
        f"Found APPEAL_SUBMITTED events for {len(unexpected)} case(s) that are "
        f"not present in appeals_df: {unexpected}"
    )
