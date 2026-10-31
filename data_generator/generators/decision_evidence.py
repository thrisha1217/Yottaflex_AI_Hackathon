"""
Generator for DecisionEvidence data.

Produces approximately 1,200 DecisionEvidence rows, linking each Decision
to 3–5 EvidenceItem rows drawn from the same case.

All columns match the ``DecisionEvidence`` bridge table defined in
``database/schema.sql``.

Columns produced
----------------
decision_id  – FK into Decision (BIGINT / sequential INT)
evidence_id  – FK into EvidenceItem (VARCHAR 80)

Composite PK ``(decision_id, evidence_id)`` is guaranteed unique.
"""

import random

import pandas as pd

from data_generator.config import TARGET_DECISION_EVIDENCE

# ------------------------------------------------------------------ #
# Constants                                                            #
# ------------------------------------------------------------------ #

# Number of evidence items selected per decision (inclusive bounds).
_MIN_EVIDENCE_PER_DECISION = 3
_MAX_EVIDENCE_PER_DECISION = 5

# Acceptable row-count tolerance band around TARGET_DECISION_EVIDENCE.
_ROW_COUNT_LOW  = 900
_ROW_COUNT_HIGH = 1500


# ------------------------------------------------------------------ #
# Public API                                                           #
# ------------------------------------------------------------------ #


def generate_decision_evidence(
    rng: random.Random,
    decisions_df: pd.DataFrame,
    evidence_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate approximately 1,200 DecisionEvidence rows.

    For each decision, 3–5 evidence items are sampled from the pool of
    evidence items that belong to the same ``case_id`` as the decision.
    If a case has fewer than 3 evidence items, all of them are used.

    Parameters
    ----------
    rng:
        ``random.Random`` instance seeded externally.  *All* randomness
        flows through this object.
    decisions_df:
        DataFrame produced by ``generate_decisions()``; must contain
        columns ``decision_id`` and ``case_id``.
    evidence_df:
        DataFrame produced by ``generate_evidence_items()``; must contain
        columns ``evidence_id`` and ``case_id``.

    Returns
    -------
    pd.DataFrame
        Columns: decision_id, evidence_id
        Composite PK ``(decision_id, evidence_id)`` is unique.
    """
    # ----------------------------------------------------------------
    # 1. Build lookup: case_id → list[evidence_id]
    # ----------------------------------------------------------------
    case_evidence_map: dict[str, list] = {}
    for _, row in evidence_df.iterrows():
        cid = row["case_id"]
        if cid not in case_evidence_map:
            case_evidence_map[cid] = []
        case_evidence_map[cid].append(row["evidence_id"])

    # ----------------------------------------------------------------
    # 2. Build rows — one row per (decision_id, evidence_id) pair
    # ----------------------------------------------------------------
    rows = []

    for _, decision_row in decisions_df.iterrows():
        decision_id = decision_row["decision_id"]
        case_id     = decision_row["case_id"]

        pool = case_evidence_map.get(case_id, [])

        if len(pool) == 0:
            # No evidence for this case — skip (shouldn't happen with
            # well-formed upstream data, but guard defensively).
            continue

        if len(pool) < _MIN_EVIDENCE_PER_DECISION:
            # Fewer items than the minimum; use all of them.
            selected = pool[:]
        else:
            # Pick 3–5 items without replacement.
            k = rng.randint(_MIN_EVIDENCE_PER_DECISION, _MAX_EVIDENCE_PER_DECISION)
            # Cap k at the pool size to avoid ValueError from rng.sample.
            k = min(k, len(pool))
            selected = rng.sample(pool, k)

        for evidence_id in selected:
            rows.append({
                "decision_id": decision_id,
                "evidence_id": evidence_id,
            })

    # ----------------------------------------------------------------
    # 3. Assemble DataFrame
    # ----------------------------------------------------------------
    df = pd.DataFrame(rows, columns=["decision_id", "evidence_id"])

    # ----------------------------------------------------------------
    # 4. Sanity assertions
    # ----------------------------------------------------------------
    # No duplicate composite PK
    assert not df.duplicated(subset=["decision_id", "evidence_id"]).any(), (
        "Composite PK (decision_id, evidence_id) must be unique — "
        "duplicate pairs were found."
    )

    # All evidence_id values exist in evidence_df
    valid_evidence_ids = set(evidence_df["evidence_id"])
    invalid_evidence   = ~df["evidence_id"].isin(valid_evidence_ids)
    assert not invalid_evidence.any(), (
        f"Found {invalid_evidence.sum()} row(s) with evidence_id values "
        "not present in evidence_df."
    )

    # All decision_id values exist in decisions_df
    valid_decision_ids = set(decisions_df["decision_id"])
    invalid_decisions  = ~df["decision_id"].isin(valid_decision_ids)
    assert not invalid_decisions.any(), (
        f"Found {invalid_decisions.sum()} row(s) with decision_id values "
        "not present in decisions_df."
    )

    # Row count within acceptable range
    assert _ROW_COUNT_LOW <= len(df) <= _ROW_COUNT_HIGH, (
        f"Expected between {_ROW_COUNT_LOW} and {_ROW_COUNT_HIGH} "
        f"DecisionEvidence rows, got {len(df)}."
    )

    return df
