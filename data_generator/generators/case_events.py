"""
Generator for CaseEvent data.

Produces 3,000+ CaseEvent rows — one sequence of events per IntegrityCase.

All columns match the ``CaseEvent`` table defined in ``database/schema.sql``.
This table is INSERT-only by convention: no UPDATE or DELETE.

Columns produced
----------------
event_id        – sequential INT starting at 1 (matches AUTO_INCREMENT PK)
case_id         – FK into IntegrityCase
event_type      – one of the defined lifecycle event types (see below)
actor_role      – role that performed the action
actor_ref       – None (not tracked at generation time)
previous_status – None (not tracked at generation time)
new_status      – None (not tracked at generation time)
event_details   – None (not tracked at generation time)
occurred_at     – strictly ascending datetime within each case

Event sequence per case
-----------------------
All cases get events 1–5 in order (accumulated deltas from opened_at):

  1. CASE_CREATED       delta = 0  days  (occurred_at == opened_at)
  2. REVIEWER_ASSIGNED  delta = rng.randint(1,  3) days
  3. EVIDENCE_ADDED     delta = rng.randint(1,  5) days
  4. STATUS_CHANGED     delta = rng.randint(1,  7) days
  5. DECISION_RECORDED  delta = rng.randint(5, 20) days

Cases whose case_id appears in appeals_df also get:

  6. APPEAL_SUBMITTED   delta = rng.randint(1, 10) days (after DECISION_RECORDED)

To meet the 3,000+ row requirement (300 cases × 5 base events = 1,500), each case
additionally receives between 5 and 10 supplemental events sampled uniformly at
random from a pool of optional lifecycle event types (EVIDENCE_ADDED, STATUS_CHANGED,
REVIEWER_ASSIGNED, COMMENT_ADDED, DOCUMENT_ATTACHED).  These supplemental events are
interleaved chronologically between CASE_CREATED and DECISION_RECORDED by inserting
them before the DECISION_RECORDED step, each separated by a rng.randint(1, 3) day
delta.  This guarantees both strict ascending order and the ≥ 3,000 row target.

Accumulated deltas guarantee strictly ascending occurred_at within each case.
"""

import random
from datetime import datetime, timedelta

import pandas as pd

from data_generator.config import TARGET_EVENTS

# ------------------------------------------------------------------ #
# Constants                                                            #
# ------------------------------------------------------------------ #

# Optional supplemental event types that can be interleaved between
# EVIDENCE_ADDED and DECISION_RECORDED to increase the total event count
# towards the 3,000+ target without violating ordering invariants.
_SUPPLEMENTAL_EVENT_TYPES = [
    "EVIDENCE_ADDED",
    "STATUS_CHANGED",
    "REVIEWER_ASSIGNED",
    "COMMENT_ADDED",
    "DOCUMENT_ATTACHED",
]

# How many supplemental events to add per case (uniform range).
# 300 cases × (5 base + 5 to 10 supplemental) = 3,000–4,500 total
# (plus ~90 APPEAL_SUBMITTED events).
_MIN_SUPPLEMENTAL = 5
_MAX_SUPPLEMENTAL = 10

# Actor roles mapped to each event type
_ACTOR_ROLES = {
    "CASE_CREATED":       "SYSTEM",
    "REVIEWER_ASSIGNED":  "ACADEMIC_ADMIN",
    "EVIDENCE_ADDED":     "REVIEWER",
    "STATUS_CHANGED":     "REVIEWER",
    "DECISION_RECORDED":  "REVIEWER",
    "APPEAL_SUBMITTED":   "LEARNER",
    "COMMENT_ADDED":      "REVIEWER",
    "DOCUMENT_ATTACHED":  "REVIEWER",
}


# ------------------------------------------------------------------ #
# Public API                                                           #
# ------------------------------------------------------------------ #


def generate_case_events(
    rng: random.Random,
    cases_df: pd.DataFrame,
    appeals_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate 3,000+ CaseEvent rows in strict chronological order per case.

    Parameters
    ----------
    rng:
        ``random.Random`` instance seeded externally.  *All* randomness
        flows through this object.
    cases_df:
        DataFrame produced by ``generate_integrity_cases()``; must
        contain columns ``case_id`` and ``opened_at``.
    appeals_df:
        DataFrame produced by ``generate_appeals()``; must contain
        column ``case_id``.

    Returns
    -------
    pd.DataFrame
        Columns: event_id, case_id, event_type, actor_role, actor_ref,
                 previous_status, new_status, event_details, occurred_at
    """
    # ----------------------------------------------------------------
    # 1. Build the set of case IDs that have an appeal
    # ----------------------------------------------------------------
    appeal_case_ids: set[str] = set(appeals_df["case_id"].tolist())

    # ----------------------------------------------------------------
    # 2. Build rows — one event sequence per case
    # ----------------------------------------------------------------
    rows = []
    event_id = 1

    for _, case_row in cases_df.iterrows():
        case_id: str = case_row["case_id"]

        opened_at: datetime = case_row["opened_at"]
        if isinstance(opened_at, pd.Timestamp):
            opened_at = opened_at.to_pydatetime()

        # Accumulate deltas from opened_at — guarantees strict ascending order
        current: datetime = opened_at

        # ---- Event 1: CASE_CREATED (delta = 0, occurred_at == opened_at) ----
        rows.append({
            "event_id":        event_id,
            "case_id":         case_id,
            "event_type":      "CASE_CREATED",
            "actor_role":      _ACTOR_ROLES["CASE_CREATED"],
            "actor_ref":       None,
            "previous_status": None,
            "new_status":      None,
            "event_details":   None,
            "occurred_at":     current,
        })
        event_id += 1

        # ---- Event 2: REVIEWER_ASSIGNED — delta 1–3 days ----
        current = current + timedelta(days=rng.randint(1, 3))
        rows.append({
            "event_id":        event_id,
            "case_id":         case_id,
            "event_type":      "REVIEWER_ASSIGNED",
            "actor_role":      _ACTOR_ROLES["REVIEWER_ASSIGNED"],
            "actor_ref":       None,
            "previous_status": None,
            "new_status":      None,
            "event_details":   None,
            "occurred_at":     current,
        })
        event_id += 1

        # ---- Event 3: EVIDENCE_ADDED — delta 1–5 days ----
        current = current + timedelta(days=rng.randint(1, 5))
        rows.append({
            "event_id":        event_id,
            "case_id":         case_id,
            "event_type":      "EVIDENCE_ADDED",
            "actor_role":      _ACTOR_ROLES["EVIDENCE_ADDED"],
            "actor_ref":       None,
            "previous_status": None,
            "new_status":      None,
            "event_details":   None,
            "occurred_at":     current,
        })
        event_id += 1

        # ---- Event 4: STATUS_CHANGED — delta 1–7 days ----
        current = current + timedelta(days=rng.randint(1, 7))
        rows.append({
            "event_id":        event_id,
            "case_id":         case_id,
            "event_type":      "STATUS_CHANGED",
            "actor_role":      _ACTOR_ROLES["STATUS_CHANGED"],
            "actor_ref":       None,
            "previous_status": None,
            "new_status":      None,
            "event_details":   None,
            "occurred_at":     current,
        })
        event_id += 1

        # ---- Supplemental events (5–10 per case) — delta 1–3 days each ----
        # These optional events are interleaved before DECISION_RECORDED to
        # bring the total row count above 3,000 while preserving ordering.
        n_supplemental = rng.randint(_MIN_SUPPLEMENTAL, _MAX_SUPPLEMENTAL)
        for _ in range(n_supplemental):
            current = current + timedelta(days=rng.randint(1, 3))
            supp_type = rng.choice(_SUPPLEMENTAL_EVENT_TYPES)
            rows.append({
                "event_id":        event_id,
                "case_id":         case_id,
                "event_type":      supp_type,
                "actor_role":      _ACTOR_ROLES[supp_type],
                "actor_ref":       None,
                "previous_status": None,
                "new_status":      None,
                "event_details":   None,
                "occurred_at":     current,
            })
            event_id += 1

        # ---- Event 5: DECISION_RECORDED — delta 5–20 days ----
        current = current + timedelta(days=rng.randint(5, 20))
        decision_occurred_at: datetime = current  # saved for appeal check
        rows.append({
            "event_id":        event_id,
            "case_id":         case_id,
            "event_type":      "DECISION_RECORDED",
            "actor_role":      _ACTOR_ROLES["DECISION_RECORDED"],
            "actor_ref":       None,
            "previous_status": None,
            "new_status":      None,
            "event_details":   None,
            "occurred_at":     current,
        })
        event_id += 1

        # ---- Event 6 (optional): APPEAL_SUBMITTED — delta 1–10 days ----
        if case_id in appeal_case_ids:
            current = current + timedelta(days=rng.randint(1, 10))
            rows.append({
                "event_id":        event_id,
                "case_id":         case_id,
                "event_type":      "APPEAL_SUBMITTED",
                "actor_role":      _ACTOR_ROLES["APPEAL_SUBMITTED"],
                "actor_ref":       None,
                "previous_status": None,
                "new_status":      None,
                "event_details":   None,
                "occurred_at":     current,
            })
            event_id += 1

    # ----------------------------------------------------------------
    # 3. Assemble DataFrame
    # ----------------------------------------------------------------
    df = pd.DataFrame(rows, columns=[
        "event_id",
        "case_id",
        "event_type",
        "actor_role",
        "actor_ref",
        "previous_status",
        "new_status",
        "event_details",
        "occurred_at",
    ])

    # ----------------------------------------------------------------
    # 4. Sanity assertions
    # ----------------------------------------------------------------

    # Total rows >= 3,000
    assert len(df) >= TARGET_EVENTS, (
        f"Expected at least {TARGET_EVENTS} CaseEvent rows, got {len(df)}"
    )

    # Every case has at least one CASE_CREATED event
    case_created_case_ids = set(
        df.loc[df["event_type"] == "CASE_CREATED", "case_id"]
    )
    all_case_ids = set(cases_df["case_id"])
    missing_case_created = all_case_ids - case_created_case_ids
    assert not missing_case_created, (
        f"These cases have no CASE_CREATED event: {missing_case_created}"
    )

    # Every case has at least one DECISION_RECORDED event
    decision_recorded_case_ids = set(
        df.loc[df["event_type"] == "DECISION_RECORDED", "case_id"]
    )
    missing_decision_recorded = all_case_ids - decision_recorded_case_ids
    assert not missing_decision_recorded, (
        f"These cases have no DECISION_RECORDED event: {missing_decision_recorded}"
    )

    # APPEAL_SUBMITTED events only for cases that have an appeal
    appeal_submitted_case_ids = set(
        df.loc[df["event_type"] == "APPEAL_SUBMITTED", "case_id"]
    )
    unexpected_appeal_events = appeal_submitted_case_ids - appeal_case_ids
    assert not unexpected_appeal_events, (
        f"APPEAL_SUBMITTED events found for cases not in appeals_df: "
        f"{unexpected_appeal_events}"
    )

    # occurred_at is strictly ascending within each case
    for cid, group in df.groupby("case_id", sort=False):
        timestamps = group.sort_values("event_id")["occurred_at"].tolist()
        for i in range(1, len(timestamps)):
            t_prev = pd.Timestamp(timestamps[i - 1])
            t_curr = pd.Timestamp(timestamps[i])
            assert t_curr > t_prev, (
                f"occurred_at is not strictly ascending for case {cid}: "
                f"event {i - 1} = {t_prev}, event {i} = {t_curr}"
            )

    # APPEAL_SUBMITTED.occurred_at > DECISION_RECORDED.occurred_at for each appeal case
    if not df.loc[df["event_type"] == "APPEAL_SUBMITTED"].empty:
        decision_times = (
            df.loc[df["event_type"] == "DECISION_RECORDED"]
            .set_index("case_id")["occurred_at"]
        )
        appeal_times = (
            df.loc[df["event_type"] == "APPEAL_SUBMITTED"]
            .set_index("case_id")["occurred_at"]
        )
        for cid in appeal_times.index:
            assert cid in decision_times.index, (
                f"APPEAL_SUBMITTED exists for case {cid} but no DECISION_RECORDED found"
            )
            t_decision = pd.Timestamp(decision_times[cid])
            t_appeal   = pd.Timestamp(appeal_times[cid])
            assert t_appeal > t_decision, (
                f"APPEAL_SUBMITTED.occurred_at ({t_appeal}) is not after "
                f"DECISION_RECORDED.occurred_at ({t_decision}) for case {cid}"
            )

    return df
