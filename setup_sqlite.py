"""
setup_sqlite.py

One-shot script that:
1. Creates all tables in the SQLite database (academic_integrity.db)
2. Loads all 14 CSV files from datasets/ in FK-dependency order

Run once from the project root:
    python setup_sqlite.py
"""

import os
import re
import sys
import pandas as pd
from sqlalchemy import text

# ── ensure we can import from backend ────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

# load .env before importing settings
from dotenv import load_dotenv
load_dotenv()

from backend.database import engine, Base
import backend.models  # registers all ORM models with Base.metadata

# ─────────────────────────────────────────────────────────────────────────────
# 1. Create all tables
# ─────────────────────────────────────────────────────────────────────────────

print("Creating tables...")
# SQLite doesn't support ENUMs — they map to VARCHAR automatically via SQLAlchemy
Base.metadata.create_all(bind=engine)
print("  OK Tables created")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Load CSVs in FK dependency order
# ─────────────────────────────────────────────────────────────────────────────

DATASETS = "datasets"

# (csv_filename, table_name) in insertion order respecting FK deps
LOAD_ORDER = [
    ("integrity_rules.csv",    "IntegrityRule"),
    ("learners.csv",           "Learner"),
    ("assessments.csv",        "Assessment"),
    ("reviewers.csv",          "Reviewer"),
    ("submissions.csv",        "Submission"),
    ("similarity_reports.csv", "SimilarityReport"),
    ("integrity_cases.csv",    "IntegrityCase"),
    ("case_reviewers.csv",     "CaseReviewer"),
    ("evidence_items.csv",     "EvidenceItem"),
    ("decisions.csv",          "Decision"),
    ("decision_evidence.csv",  "DecisionEvidence"),
    ("appeals.csv",            "Appeal"),
    ("appeal_reviews.csv",     "AppealReview"),
    ("case_events.csv",        "CaseEvent"),
]

def clean_df(df):
    """Replace NaN with None so SQLite stores NULL rather than the string 'nan'."""
    return df.where(pd.notnull(df), other=None)

with engine.begin() as conn:
    # Disable FK enforcement during bulk load (SQLite requires explicit pragma)
    conn.execute(text("PRAGMA foreign_keys = OFF"))

    for filename, table in LOAD_ORDER:
        path = os.path.join(DATASETS, filename)
        if not os.path.exists(path):
            print(f"  SKIP {filename} not found")
            continue

        df = clean_df(pd.read_csv(path))

        # Clear existing rows so re-runs are idempotent
        conn.execute(text(f'DELETE FROM "{table}"'))

        df.to_sql(table, con=conn, if_exists="append", index=False)
        print(f"  OK  {table:30s} {len(df):>6,} rows loaded from {filename}")

    conn.execute(text("PRAGMA foreign_keys = ON"))

print("\nDone — academic_integrity.db is ready.")

# ── Always inject post-decision evidence after base load ─────────────────────
import subprocess, sys
print("\nInjecting post-decision edge-case evidence...")
result = subprocess.run([sys.executable, "inject_post_decision_evidence.py"], capture_output=True, text=True)
if result.returncode == 0:
    for line in result.stdout.strip().splitlines():
        print(f"  {line}")
else:
    print("  Warning: injection failed —", result.stderr[:200])

print("\nSetup complete. Start the backend with:")
print("  python -m uvicorn backend.main:app --reload --port 8000")
