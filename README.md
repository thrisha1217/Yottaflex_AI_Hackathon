# Academic Integrity and Similarity Review Management System

A full-stack application that manages the complete academic-integrity lifecycle:
similarity detection → human review → case decisions → appeals → audit reporting.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+

### 1 — Install Python dependencies
```bash
pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings python-dotenv pandas faker numpy httpx pytest hypothesis
```

### 2 — Install frontend dependencies
```bash
cd frontend && npm install
```

### 3 — Create the SQLite database and load data
```bash
python setup_sqlite.py
```

### 4 — (Optional) Inject post-decision edge-case evidence
```bash
python inject_post_decision_evidence.py
```

### 5 — Start the backend API
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

### 6 — Start the frontend
```bash
cd frontend && npm run dev
```

Open **http://localhost:5173** for the dashboard.  
Open **http://localhost:8000/docs** for the interactive API explorer.

---

## Regenerating Synthetic Data

```bash
python -m data_generator.main
```

Uses fixed seed `20261022`. Running twice produces byte-identical CSVs in `datasets/`.

### Verify reproducibility
```bash
python verify_reproducibility.py
```

---

## Generating Ground Truth Labels
```bash
python generate_ground_truth.py
```

Produces `datasets/ground_truth.csv` — labelled anomaly records for evaluation.  
**Do NOT load this file into the application database.**

---

## Project Structure

```
academic-integrity-system/
├── .env                          # Local environment (DATABASE_URL, CORS_ORIGINS)
├── setup_sqlite.py               # Creates DB schema + loads all CSVs
├── inject_post_decision_evidence.py  # Injects post-decision edge-case rows
├── generate_ground_truth.py      # Produces datasets/ground_truth.csv
├── verify_reproducibility.py     # Confirms fixed-seed reproducibility
│
├── database/
│   ├── schema.sql                # MySQL DDL (Milestone 1)
│   └── data_dictionary.md        # Full field-level documentation for all 15 tables
│
├── datasets/                     # Generated CSV files (14 tables + ground truth)
│   ├── learners.csv              # 500 rows
│   ├── assessments.csv           # 50 rows
│   ├── integrity_rules.csv       # 10 rows (threshold ladder)
│   ├── reviewers.csv             # 30 rows
│   ├── submissions.csv           # 10,000 rows
│   ├── similarity_reports.csv    # 10,000 rows (~1,004 flagged)
│   ├── integrity_cases.csv       # 300 rows
│   ├── case_reviewers.csv        # 350 rows (incl. 10 CONFLICT rows)
│   ├── evidence_items.csv        # 915 rows (incl. 15 post-decision non-material)
│   ├── decisions.csv             # 300 rows
│   ├── decision_evidence.csv     # 900 rows
│   ├── appeals.csv               # 90 rows
│   ├── appeal_reviews.csv        # 80 rows
│   ├── case_events.csv           # 3,882 rows
│   ├── ground_truth.csv          # 111 labelled anomaly records (DO NOT load to DB)
│   └── ground_truth_summary.txt  # Summary of ground truth categories
│
├── data_generator/               # Synthetic data generator (Python/Pandas/Faker)
│   ├── config.py                 # SEED=20261022, all TARGET_* constants
│   ├── main.py                   # Entry point — calls generators in FK order
│   ├── generators/               # One module per table
│   └── utils/                    # id_formatter.py, date_utils.py
│
├── backend/                      # FastAPI REST API
│   ├── main.py                   # App factory — registers all 9 routers
│   ├── config.py                 # Settings (DATABASE_URL, CORS_ORIGINS)
│   ├── database.py               # SQLAlchemy engine + session (SQLite/MySQL)
│   ├── models/                   # SQLAlchemy ORM models (1 per table)
│   ├── schemas/                  # Pydantic request/response schemas
│   ├── routers/                  # FastAPI path operations (thin)
│   └── services/                 # Business logic layer
│
├── frontend/                     # React SPA (Vite + Recharts)
│   └── src/
│       ├── api/                  # Axios wrappers per domain
│       ├── components/           # Shared UI + chart components
│       ├── hooks/                # Custom React hooks
│       └── pages/                # Route-level page components
│
└── tests/                        # Property-based + unit tests (Hypothesis + pytest)
```

---

## Dataset Summary

| Table | Rows | Notes |
|---|---|---|
| Learner | 500 | Unique emails, year_of_study 1–10 |
| Assessment | 50 | 4 types distributed |
| IntegrityRule | 10 | 4-tier threshold ladder |
| Reviewer | 30 | 3 roles distributed |
| Submission | 10,000 | Unique (learner, assessment, attempt) |
| SimilarityReport | 10,000 | 1,004 flagged (review_required=TRUE) |
| IntegrityCase | 300 | All linked to flagged reports |
| CaseReviewer | 350 | 10 CONFLICT rows included |
| EvidenceItem | 915 | 15 post-decision non-material rows |
| Decision | 300 | 141 NO_VIOLATION / 92 VIOLATION / 67 INCONCLUSIVE |
| DecisionEvidence | 900 | Bridge table |
| Appeal | 90 | 32 UPHELD/OVERTURNED, 22 REMANDED |
| AppealReview | 80 | All resolved appeals have independence_verified=TRUE |
| CaseEvent | 3,882 | INSERT-only timeline per case |

---

## Ground Truth — Edge Cases

`datasets/ground_truth.csv` contains 111 labelled records across 3 categories:

| issue_type | Count | Description |
|---|---|---|
| `POST_DECISION_EVIDENCE` | 67 | Evidence added after Decision was recorded; `is_material=FALSE` |
| `FLAG_TREATED_AS_GUILT` | 34 | VIOLATION Decision on borderline score (71–80%); flag ≠ guilt |
| `REVIEWER_CONFLICT` | 10 | Reviewer declared conflict; reassignment required; history retained |

> **Note:** `APPEAL_NO_INDEPENDENT_REVIEW` = 0 rows — the API enforcement works correctly.

---

## Business Rules

| # | Rule | Enforcement |
|---|---|---|
| 1 | Similarity flag ≠ guilt | `review_required=TRUE` opens a case; only a human Decision records VIOLATION |
| 2 | Reviewer conflict → reassign | `conflict_status=CONFLICT` blocks assignment; row retained as history |
| 3 | Post-decision evidence preserved | New row with `is_material=FALSE`; original Decision immutable |
| 4 | Appeal requires independent review | `independence_verified=TRUE` required before UPHELD/OVERTURNED |
| 5 | No history overwrite | CaseEvent (INSERT-only), Decision (append-only), AuditLog |

---

## ID Conventions

| Entity | Format | Example |
|---|---|---|
| Submission | `SUB-{YYYY}-{NNNNNN}` | `SUB-2026-000001` |
| SimilarityReport | `SIM-{submission_id}-{NN}` | `SIM-SUB-2026-000001-01` |
| IntegrityCase | `INT-{YYYY}-{NNNNNN}` | `INT-2026-000001` |
| EvidenceItem | `EVD-{NNNNNN}` | `EVD-000001` |
| Appeal | `APL-{NNNNNN}` | `APL-000001` |

---

## Generator Command & Reproducibility

```bash
# Generate fresh datasets (deterministic — same output every run)
python -m data_generator.main

# Seed used
SEED = 20261022

# Verify byte-identical output across two runs
python verify_reproducibility.py
```

All outputs are synthetic. No real personal data was used. Faker generates names,
emails and text using the fixed seed. No external datasets were used or required.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/analytics/summary` | Aggregate counts |
| GET | `/analytics/similarity-distribution` | Score bucket distribution |
| GET | `/analytics/cases-over-time` | Monthly case counts |
| GET | `/analytics/outcomes-by-program` | Decision outcomes by programme |
| GET | `/analytics/top-assessments` | Top 10 assessments by case count |
| GET | `/submissions` | Paginated submissions (flagged filter) |
| GET | `/cases` | Paginated cases (status/priority filters) |
| GET | `/cases/{id}` | Full case detail |
| PATCH | `/cases/{id}/status` | Update case status |
| POST | `/cases/{id}/reviewers` | Assign reviewer |
| POST | `/cases/{id}/evidence` | Add evidence |
| POST | `/cases/{id}/decisions` | Record decision |
| POST | `/cases/{id}/appeals` | Submit appeal |
| POST | `/appeals/{id}/reviews` | Submit appeal review |
| GET | `/audit-log` | Paginated audit log |
| GET | `/audit/conflict-reassignments` | Conflict of interest report |
| GET | `/audit/post-decision-evidence` | Post-decision evidence report |
| GET | `/audit/appeals-without-independent-review` | Compliance check |
| GET | `/audit/case-event-log/{case_id}` | Full case timeline |
