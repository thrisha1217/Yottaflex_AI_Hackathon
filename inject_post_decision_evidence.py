"""
inject_post_decision_evidence.py

Injects labelled post-decision evidence rows (is_material = FALSE) directly
into datasets/evidence_items.csv, then reloads the EvidenceItem table in SQLite.

These rows represent the edge case: "evidence added after decision without
history being rewritten" (required by brief Step 5).

Run after setup_sqlite.py:
    python inject_post_decision_evidence.py
"""

import os, sys
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

DATASETS = "datasets"

# ── Load data ─────────────────────────────────────────────────────────────────
ev        = pd.read_csv(f"{DATASETS}/evidence_items.csv")
decisions = pd.read_csv(f"{DATASETS}/decisions.csv")
cases     = pd.read_csv(f"{DATASETS}/integrity_cases.csv")

# Skip if post-decision rows already exist (idempotent)
if (ev["is_material"] == False).sum() > 0:
    print(f"Post-decision evidence already injected ({(ev['is_material']==False).sum()} rows). Skipping.")
    sys.exit(0)

decisions["decided_at_dt"] = pd.to_datetime(decisions["decided_at"], errors="coerce")

# Pick 15 DECIDED cases to inject post-decision evidence on
decided_cases = cases[cases.case_status.isin(["DECIDED", "CLOSED"])].head(15)

# Get max evidence counter
def ev_num(eid):
    # New format: EVD-INT-2026-000001-003 → extract trailing number
    import re
    m = re.search(r"-(\d+)$", str(eid))
    return int(m.group(1)) if m else 0

# For injected rows use a simple global counter to avoid collisions
# Find max global sequence across all evidence IDs
import re
def global_seq(eid):
    parts = str(eid).split("-")
    try:
        return int(parts[-1])
    except:
        return 0

max_seq = max(global_seq(x) for x in ev["evidence_id"])

new_rows = []
for _, case_row in decided_cases.iterrows():
    case_id = case_row["case_id"]
    dec = decisions[decisions.case_id == case_id]
    if dec.empty:
        continue
    decided_at = dec["decided_at_dt"].iloc[0]
    if pd.isna(decided_at):
        continue

    # Count existing evidence for this case, add one more
    existing_count = len(ev[ev["case_id"] == case_id])
    new_item_no = existing_count + 1
    evidence_id = f"EVD-{case_id}-{new_item_no:03d}"
    # Add the evidence 3 days after the decision
    added_at = (decided_at + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")

    new_rows.append({
        "evidence_id":        evidence_id,
        "case_id":            case_id,
        "evidence_type":      "DOCUMENT",
        "description":        (
            "Post-decision supporting document submitted by learner after outcome was recorded. "
            "Preserved as non-material evidence per audit policy."
        ),
        "evidence_reference": f"post_decision_docs/{case_id}_supplementary.pdf",
        "added_by_role":      "LEARNER",
        "added_by_ref":       "",
        "added_at":           added_at,
        "is_material":        False,  # KEY: marks as post-decision / non-material
    })

new_df = pd.DataFrame(new_rows)
ev_updated = pd.concat([ev, new_df], ignore_index=True)
ev_updated.to_csv(f"{DATASETS}/evidence_items.csv", index=False)
print(f"Injected {len(new_rows)} post-decision evidence rows -> evidence_items.csv")
print(f"Total evidence rows now: {len(ev_updated)}")

# ── Reload EvidenceItem table in SQLite ────────────────────────────────────────
from sqlalchemy import text
from backend.database import engine

with engine.begin() as conn:
    conn.execute(text('PRAGMA foreign_keys = OFF'))
    conn.execute(text('DELETE FROM "EvidenceItem"'))
    ev_updated.where(pd.notnull(ev_updated), other=None).to_sql(
        "EvidenceItem", con=conn, if_exists="append", index=False
    )
    conn.execute(text('PRAGMA foreign_keys = ON'))

print(f"EvidenceItem table reloaded in SQLite.")
non_material = ev_updated[ev_updated["is_material"] == False]
print(f"Non-material rows in DB: {len(non_material)}")
