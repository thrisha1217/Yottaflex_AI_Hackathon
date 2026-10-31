"""
generate_ground_truth.py

Produces datasets/ground_truth.csv — labelled anomaly and edge-case records.

Four edge-case categories (per brief):
  1. FLAG_TREATED_AS_GUILT   — case opened on a flagged report but Decision = VIOLATION
                               with similarity_score < 71 (false positive territory).
                               Represents the risk of treating a flag as automatic guilt.

  2. REVIEWER_CONFLICT       — CaseReviewer rows with conflict_status = CONFLICT.
                               These must be reassigned; retaining history is correct behaviour.

  3. POST_DECISION_EVIDENCE  — EvidenceItem rows added after the case Decision was recorded
                               (added_at > decided_at). These have is_material = FALSE.
                               Represents evidence added without decision history being rewritten.

  4. APPEAL_NO_INDEPENDENT_REVIEW — Appeals with appeal_status UPHELD/OVERTURNED but
                                    where no AppealReview row has independence_verified = TRUE.
                                    By design this should be empty (API guards against it);
                                    if any rows appear here it is a data-integrity violation.

The file is ground-truth only — it is NOT loaded into the application database.
Never use it as an input feature for ML training without proper feature/label separation.

Run:
    python generate_ground_truth.py
Output:
    datasets/ground_truth.csv
    datasets/ground_truth_summary.txt
"""

import os
import sys
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

DATASETS = "datasets"

# ── Load CSVs ─────────────────────────────────────────────────────────────────
cases     = pd.read_csv(f"{DATASETS}/integrity_cases.csv")
decisions = pd.read_csv(f"{DATASETS}/decisions.csv")
cr        = pd.read_csv(f"{DATASETS}/case_reviewers.csv")
appeals   = pd.read_csv(f"{DATASETS}/appeals.csv")
ar        = pd.read_csv(f"{DATASETS}/appeal_reviews.csv")
ev        = pd.read_csv(f"{DATASETS}/evidence_items.csv")
reports   = pd.read_csv(f"{DATASETS}/similarity_reports.csv")

records = []

# ── 1. FLAG_TREATED_AS_GUILT ─────────────────────────────────────────────────
# Cases where decision = VIOLATION but the report score was borderline (71–80)
# This represents the risk of a reviewer treating a flag as automatic guilt
# rather than weighing evidence independently.

merged = (
    decisions[decisions.decision_outcome == "VIOLATION"]
    .merge(cases, on="case_id")
    .merge(reports, on="report_id", how="left")
)
borderline = merged[merged.similarity_score.between(71, 80)]
for _, row in borderline.iterrows():
    records.append({
        "issue_id":         f"GT-GUILT-{row['case_id']}",
        "issue_type":       "FLAG_TREATED_AS_GUILT",
        "entity_type":      "Decision",
        "entity_id":        str(row["decision_id"]),
        "related_case_id":  row["case_id"],
        "related_report_id": row.get("report_id", ""),
        "similarity_score": row.get("similarity_score", ""),
        "decision_outcome": row["decision_outcome"],
        "expected_outcome": "INVESTIGATION_REQUIRED — score in borderline range; flag ≠ guilt",
        "conflict_reason":  "",
        "description": (
            f"Case {row['case_id']} recorded VIOLATION with similarity score "
            f"{row.get('similarity_score', '?')}% (borderline 71–80%). "
            "A flag triggers review, not automatic guilt. "
            "The decision should be based on evidence, not score alone."
        ),
        "generated_at": datetime.utcnow().isoformat(),
    })

# ── 2. REVIEWER_CONFLICT ─────────────────────────────────────────────────────
# All CaseReviewer rows with conflict_status = CONFLICT.
# These are valid history rows — the reviewer was correctly unassigned.
# Labelled here so evaluators can verify the conflict was handled properly.

conflicts = cr[cr.conflict_status == "CONFLICT"]
for _, row in conflicts.iterrows():
    records.append({
        "issue_id":         f"GT-CONFLICT-{row['assignment_id']}",
        "issue_type":       "REVIEWER_CONFLICT",
        "entity_type":      "CaseReviewer",
        "entity_id":        str(row["assignment_id"]),
        "related_case_id":  row["case_id"],
        "related_report_id": "",
        "similarity_score": "",
        "decision_outcome": "",
        "expected_outcome": "Reviewer reassigned; conflict row retained as history",
        "conflict_reason":  str(row.get("conflict_reason", "")),
        "description": (
            f"Reviewer {row['reviewer_id']} declared conflict on case {row['case_id']}. "
            f"Reason: {row.get('conflict_reason', 'N/A')}. "
            "Row retained as immutable history; unassigned_at should be set."
        ),
        "generated_at": datetime.utcnow().isoformat(),
    })

# ── 3. POST_DECISION_EVIDENCE ─────────────────────────────────────────────────
# Evidence added after the case decision was recorded.
# In the live dataset these have is_material = FALSE (set by the API).
# In the CSV dataset we identify them by comparing added_at vs decided_at.

ev["added_at_dt"]   = pd.to_datetime(ev["added_at"], errors="coerce")
decisions["decided_at_dt"] = pd.to_datetime(decisions["decided_at"], errors="coerce")

ev_cases = ev.merge(decisions[["case_id", "decided_at_dt", "decision_id"]], on="case_id", how="left")
post_dec = ev_cases[ev_cases.added_at_dt > ev_cases.decided_at_dt]

for _, row in post_dec.iterrows():
    records.append({
        "issue_id":         f"GT-POSTDEC-{row['evidence_id']}",
        "issue_type":       "POST_DECISION_EVIDENCE",
        "entity_type":      "EvidenceItem",
        "entity_id":        row["evidence_id"],
        "related_case_id":  row["case_id"],
        "related_report_id": "",
        "similarity_score": "",
        "decision_outcome": "",
        "expected_outcome": "is_material = FALSE; Decision record unchanged",
        "conflict_reason":  "",
        "description": (
            f"Evidence {row['evidence_id']} was added to case {row['case_id']} on "
            f"{row['added_at']} — after the Decision recorded on "
            f"{row.get('decided_at', '?')}. "
            "Must be preserved with is_material=FALSE; original Decision must not be modified."
        ),
        "generated_at": datetime.utcnow().isoformat(),
    })

# ── 4. APPEAL_NO_INDEPENDENT_REVIEW ──────────────────────────────────────────
# Appeals that are UPHELD or OVERTURNED without an AppealReview where
# independence_verified = TRUE. By design this should be zero (API guards against it).
# If rows appear here it is a data-integrity violation.

independent_ids = set(ar[ar.independence_verified == True]["appeal_id"].tolist())
resolved = appeals[appeals.appeal_status.isin(["UPHELD", "OVERTURNED"])]
violations = resolved[~resolved.appeal_id.isin(independent_ids)]

for _, row in violations.iterrows():
    records.append({
        "issue_id":         f"GT-NOREVIEW-{row['appeal_id']}",
        "issue_type":       "APPEAL_NO_INDEPENDENT_REVIEW",
        "entity_type":      "Appeal",
        "entity_id":        row["appeal_id"],
        "related_case_id":  row["case_id"],
        "related_report_id": "",
        "similarity_score": "",
        "decision_outcome": row["appeal_status"],
        "expected_outcome": "AppealReview with independence_verified=TRUE required",
        "conflict_reason":  "",
        "description": (
            f"Appeal {row['appeal_id']} on case {row['case_id']} has status "
            f"{row['appeal_status']} but no independent AppealReview found. "
            "This is a data-integrity violation — the API should have prevented this."
        ),
        "generated_at": datetime.utcnow().isoformat(),
    })

# ── Write ground_truth.csv ────────────────────────────────────────────────────
gt = pd.DataFrame(records, columns=[
    "issue_id", "issue_type", "entity_type", "entity_id",
    "related_case_id", "related_report_id", "similarity_score",
    "decision_outcome", "expected_outcome", "conflict_reason",
    "description", "generated_at",
])

out_path = f"{DATASETS}/ground_truth.csv"
gt.to_csv(out_path, index=False)

# ── Summary ───────────────────────────────────────────────────────────────────
summary_lines = [
    "ground_truth.csv — Generation Summary",
    "=" * 50,
    f"Generated at: {datetime.utcnow().isoformat()} UTC",
    f"Total labelled records: {len(gt)}",
    "",
    "Breakdown by issue_type:",
]
for issue_type, count in gt["issue_type"].value_counts().items():
    summary_lines.append(f"  {issue_type:<40} {count:>4} rows")

summary_lines += [
    "",
    "IMPORTANT: This file is ground-truth only.",
    "Do NOT load it into the application database.",
    "Do NOT use it as an input feature without proper feature/label separation.",
]

summary_text = "\n".join(summary_lines)
print(summary_text)

summary_path = f"{DATASETS}/ground_truth_summary.txt"
with open(summary_path, "w") as f:
    f.write(summary_text)

print(f"\nFiles written:")
print(f"  {out_path}")
print(f"  {summary_path}")
