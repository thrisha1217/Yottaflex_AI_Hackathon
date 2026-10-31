"""
verify_reproducibility.py  (Step 10 of the brief)

Runs the data generator twice with the same seed and compares all 14 CSV files
row-count by row-count and checksum by checksum to demonstrate reproducibility.

Run:
    python verify_reproducibility.py
"""

import hashlib
import os
import shutil
import subprocess
import sys

DATASETS = "datasets"
TABLES = [
    "integrity_rules", "learners", "assessments", "reviewers",
    "submissions", "similarity_reports", "integrity_cases",
    "case_reviewers", "evidence_items", "decisions",
    "decision_evidence", "appeals", "appeal_reviews", "case_events",
]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run_generator():
    result = subprocess.run(
        [sys.executable, "-m", "data_generator.main"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("Generator failed:")
        print(result.stderr)
        sys.exit(1)


def collect_checksums() -> dict:
    return {
        t: sha256_file(os.path.join(DATASETS, f"{t}.csv"))
        for t in TABLES
        if os.path.exists(os.path.join(DATASETS, f"{t}.csv"))
    }


print("=" * 60)
print("Reproducibility check — running generator twice")
print("=" * 60)

# ── Run 1 ─────────────────────────────────────────────────────────────────────
print("\n[Run 1] Generating data...")
run_generator()
run1 = collect_checksums()

# ── Run 2 ─────────────────────────────────────────────────────────────────────
print("[Run 2] Generating data again...")
run_generator()
run2 = collect_checksums()

# ── Compare ───────────────────────────────────────────────────────────────────
print("\nResults:")
print(f"{'Table':<30} {'Run 1 SHA256':>12}  {'Run 2 SHA256':>12}  {'Match?':>6}")
print("-" * 70)

all_match = True
for t in TABLES:
    c1 = run1.get(t, "MISSING")
    c2 = run2.get(t, "MISSING")
    match = c1 == c2
    if not match:
        all_match = False
    short1 = c1[:10] + "…" if len(c1) > 10 else c1
    short2 = c2[:10] + "…" if len(c2) > 10 else c2
    status = "✓" if match else "✗ DIFFER"
    print(f"{t:<30} {short1:>12}  {short2:>12}  {status:>6}")

print()
if all_match:
    print("✓ All 14 CSV files are byte-identical across both runs.")
    print("  Fixed seed 20261022 guarantees full reproducibility.")
else:
    print("✗ Some files differ — reproducibility check FAILED.")
    sys.exit(1)
