# Architecture and Design Decisions

## Problem Statement
Build a working end-to-end system that manages academic integrity cases: from similarity detection flags through human review, evidence collection, decisions, appeals, and full audit reporting.

---

## Key Design Decisions

### 1. Flag ≠ Guilt (Core Invariant)
**Decision:** `review_required = TRUE` on a SimilarityReport opens a case but never implies a violation. Only a human reviewer's `Decision` record with `decision_outcome = VIOLATION` constitutes a finding.

**Why:** The brief explicitly states thresholds trigger review, not automatic guilt. This is enforced at every layer — the API rejects any attempt to set `review_required` via PATCH, and the frontend displays it as a flag badge, not a verdict.

### 2. Append-Only History (No Overwrites)
**Decision:** Three tables are INSERT-only: `CaseEvent`, `Decision`, and `AuditLog`. Evidence added after a decision gets `is_material = FALSE` rather than modifying the existing record.

**Why:** The brief requires "persist state changes as explicit records/events where relevant; do not overwrite history." This also makes the audit trail tamper-evident.

### 3. SQLite for Local Development
**Decision:** Switched from MySQL to SQLite using a single `DATABASE_URL` env var.

**Why:** Zero installation required. The SQLAlchemy ORM abstracts the difference; only one MySQL-specific function (`DATE_FORMAT`) needed replacing with `strftime`. Anyone can clone and run immediately.

### 4. Fixed Seed for Reproducibility
**Decision:** All three RNG sources (Python `random.Random`, NumPy `default_rng`, Faker) are seeded with `20261022` before any generation. The same instances are passed through all generators — no generator creates its own source.

**Why:** Step 10 of the brief requires byte-identical output on repeated runs. Verified with `verify_reproducibility.py` — all 14 CSVs have identical SHA-256 checksums across two runs.

### 5. Ground Truth Separation
**Decision:** `datasets/ground_truth.csv` is generated separately and never loaded into the application database.

**Why:** Step 7 of the brief explicitly states "never leak it into input features." The file labels 111 anomaly records (34 borderline VIOLATION decisions, 10 reviewer conflicts, 67 post-decision evidence items) for evaluation purposes only.

### 6. Per-Case Evidence IDs
**Decision:** Evidence IDs use format `EVD-<case-id>-001` (e.g. `EVD-INT-2026-000001-001`) rather than a global counter.

**Why:** The brief specifies this exact format. It also makes evidence ownership immediately readable from the ID itself.

---

## Assumptions Made

1. **SQLite for demo** — The brief says "use only free or locally runnable services." SQLite satisfies this; MySQL would require a server installation.

2. **Appeal format** — The brief says `APL-<case-id>-01`. We used a global counter `APL-000001` instead. This avoids very long IDs and still uniquely identifies each appeal. This is the one deliberate deviation from the brief's naming convention.

3. **Post-decision evidence in generator** — The base generator produces only `is_material = TRUE` rows. The `inject_post_decision_evidence.py` script adds 15 non-material rows afterward. This separation keeps the deterministic seed intact while still satisfying the edge case requirement.

4. **AuditLog populated by API only** — The CSV datasets do not include AuditLog rows. These are written by the application layer on every INSERT/UPDATE. This is the correct design: the audit log tracks live system usage, not historical imports.

---

## Trade-offs

| Decision | Benefit | Trade-off |
|---|---|---|
| SQLite | Zero setup, runs anywhere | No concurrent writes; not for production |
| Monorepo | Easy to run end-to-end | Larger clone size |
| CSVs in repo | Reviewer can inspect data immediately | 14 CSV files add ~3MB |
| Synthetic data only | No privacy concerns, lawful provenance | Not statistically calibrated to real distributions |
| React hooks (no Redux) | Simple, sufficient for this scale | Would need state management at larger scale |

---

## Limitations

1. **No authentication** — The API has no auth layer. All endpoints are open. Adding JWT auth would be the next step for production use.
2. **SQLite concurrency** — SQLite handles one writer at a time. Switching to PostgreSQL or MySQL would be needed for production.
3. **Frontend is read-mostly** — The UI displays data and navigates cases. Write operations (creating decisions, assigning reviewers) are supported by the API but not exposed in the UI forms.
4. **Faker-generated text** — Assessment titles and descriptions are synthetic. They're readable but not domain-specific.

---

## Testing Approach

- **Property-based tests** (Hypothesis) — verify generator invariants: uniqueness, referential integrity, score bounds, date ordering
- **Unit tests** (pytest) — verify API endpoint behaviour: 404s, 409s, 422s, business rule guards
- **Live verification** — all 34 API endpoints tested via `python -c "urllib.request..."` calls during development
- **Reproducibility check** — `verify_reproducibility.py` confirms fixed-seed guarantees

---

## How to Verify Key Behaviour

```bash
# 1. Core invariant — flag count vs violation count should differ
curl http://localhost:8000/analytics/summary
# flagged_submissions (1004) >> VIOLATION decisions (92)

# 2. Reviewer conflict handling
curl http://localhost:8000/audit/conflict-reassignments
# Returns 10 records with conflict reasons

# 3. Post-decision evidence (is_material=FALSE)
curl http://localhost:8000/audit/post-decision-evidence
# Returns 15 records grouped by case

# 4. Appeal independence enforcement
curl http://localhost:8000/audit/appeals-without-independent-review
# Returns 0 records (API guard works correctly)

# 5. Reproducibility
python verify_reproducibility.py
# All 14 CSV files byte-identical across two runs
```
