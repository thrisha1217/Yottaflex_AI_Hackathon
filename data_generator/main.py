"""
Entry point for the academic integrity synthetic data generator.

Wires all table generators together in FK dependency order and writes
each resulting DataFrame to ``datasets/`` as a CSV file.

Usage
-----
    python -m data_generator.main
    # or directly:
    python data_generator/main.py

Output
------
All CSV files are written to the directory specified by ``OUTPUT_DIR``
in ``data_generator.config`` (default: ``datasets/``).

Files produced (in write order, matching FK dependency order):

    integrity_rules.csv
    learners.csv
    assessments.csv
    reviewers.csv
    submissions.csv
    similarity_reports.csv
    integrity_cases.csv
    case_reviewers.csv
    evidence_items.csv
    decisions.csv
    decision_evidence.csv
    appeals.csv
    appeal_reviews.csv
    case_events.csv
"""

import os
import random

import numpy as np
from faker import Faker

from data_generator.config import OUTPUT_DIR, SEED
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


def init_rng():
    """Initialise and return the three seeded random sources used by all generators.

    Returns
    -------
    tuple[random.Random, numpy.random.Generator, Faker]
        ``(rng, nprng, faker)`` — all seeded with ``SEED = 20261022``.
    """
    rng = random.Random(SEED)
    nprng = np.random.default_rng(SEED)
    faker = Faker()
    Faker.seed(SEED)
    return rng, nprng, faker


def main():
    """Generate all synthetic data tables and write them to CSV files.

    Generators are called in FK dependency order so that parent tables
    are always available before child tables that reference them.
    """
    # ------------------------------------------------------------------
    # Initialise random sources
    # ------------------------------------------------------------------
    rng, nprng, faker = init_rng()

    # ------------------------------------------------------------------
    # Ensure the output directory exists
    # ------------------------------------------------------------------
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ------------------------------------------------------------------
    # Helper — write a DataFrame to CSV and print progress
    # ------------------------------------------------------------------
    def _write(df, filename):
        path = os.path.join(OUTPUT_DIR, filename)
        df.to_csv(path, index=False)
        print(f"  OK  {filename:40s}  {len(df):>7,} rows  ->  {path}")

    print(f"\nAcademic Integrity Data Generator  (seed={SEED})")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. IntegrityRule  (no FK dependencies)
    # ------------------------------------------------------------------
    rules_df = generate_integrity_rules(rng)
    _write(rules_df, "integrity_rules.csv")

    # ------------------------------------------------------------------
    # 2. Learner  (no FK dependencies)
    # ------------------------------------------------------------------
    learners_df = generate_learners(rng, nprng, faker)
    _write(learners_df, "learners.csv")

    # ------------------------------------------------------------------
    # 3. Assessment  (no FK dependencies)
    # ------------------------------------------------------------------
    assessments_df = generate_assessments(rng, faker)
    _write(assessments_df, "assessments.csv")

    # ------------------------------------------------------------------
    # 4. Reviewer  (no FK dependencies)
    # ------------------------------------------------------------------
    reviewers_df = generate_reviewers(rng, faker)
    _write(reviewers_df, "reviewers.csv")

    # ------------------------------------------------------------------
    # 5. Submission  (FK → Learner, Assessment)
    # ------------------------------------------------------------------
    submissions_df = generate_submissions(rng, nprng, learners_df, assessments_df)
    _write(submissions_df, "submissions.csv")

    # ------------------------------------------------------------------
    # 6. SimilarityReport  (FK → Submission, IntegrityRule)
    # ------------------------------------------------------------------
    reports_df = generate_similarity_reports(nprng, submissions_df, rules_df)
    _write(reports_df, "similarity_reports.csv")

    # ------------------------------------------------------------------
    # 7. IntegrityCase  (FK → SimilarityReport)
    # ------------------------------------------------------------------
    cases_df = generate_integrity_cases(rng, reports_df)
    _write(cases_df, "integrity_cases.csv")

    # ------------------------------------------------------------------
    # 8. CaseReviewer  (FK → IntegrityCase, Reviewer)
    # ------------------------------------------------------------------
    case_reviewers_df = generate_case_reviewers(rng, cases_df, reviewers_df)
    _write(case_reviewers_df, "case_reviewers.csv")

    # ------------------------------------------------------------------
    # 9. EvidenceItem  (FK → IntegrityCase)
    # ------------------------------------------------------------------
    evidence_df = generate_evidence_items(rng, faker, cases_df)
    _write(evidence_df, "evidence_items.csv")

    # ------------------------------------------------------------------
    # 10. Decision  (FK → IntegrityCase, Reviewer)
    # ------------------------------------------------------------------
    decisions_df = generate_decisions(rng, faker, cases_df, reviewers_df)
    _write(decisions_df, "decisions.csv")

    # ------------------------------------------------------------------
    # 11. DecisionEvidence  (FK → Decision, EvidenceItem)
    # ------------------------------------------------------------------
    decision_evidence_df = generate_decision_evidence(rng, decisions_df, evidence_df)
    _write(decision_evidence_df, "decision_evidence.csv")

    # ------------------------------------------------------------------
    # 12. Appeal  (FK → IntegrityCase, Decision, Learner)
    # ------------------------------------------------------------------
    appeals_df = generate_appeals(rng, faker, cases_df, decisions_df, learners_df)
    _write(appeals_df, "appeals.csv")

    # ------------------------------------------------------------------
    # 13. AppealReview  (FK → Appeal, CaseReviewer, Reviewer)
    # ------------------------------------------------------------------
    appeal_reviews_df = generate_appeal_reviews(
        rng, faker, appeals_df, case_reviewers_df, reviewers_df
    )
    _write(appeal_reviews_df, "appeal_reviews.csv")

    # ------------------------------------------------------------------
    # 14. CaseEvent  (FK → IntegrityCase, Appeal)
    # ------------------------------------------------------------------
    events_df = generate_case_events(rng, cases_df, appeals_df)
    _write(events_df, "case_events.csv")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    total_rows = sum([
        len(rules_df), len(learners_df), len(assessments_df), len(reviewers_df),
        len(submissions_df), len(reports_df), len(cases_df), len(case_reviewers_df),
        len(evidence_df), len(decisions_df), len(decision_evidence_df),
        len(appeals_df), len(appeal_reviews_df), len(events_df),
    ])
    print("=" * 60)
    print(f"Done. {14} tables written to '{OUTPUT_DIR}'  ({total_rows:,} total rows)\n")


if __name__ == "__main__":
    main()
