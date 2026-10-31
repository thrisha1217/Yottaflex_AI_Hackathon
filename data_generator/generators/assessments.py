"""
Generator for Assessment reference data.

Produces exactly 50 Assessment rows with realistic titles, randomised
course codes, and assessment types distributed across the four enum
values.  All columns match the ``Assessment`` table defined in
database/schema.sql.
"""

import pandas as pd
from datetime import datetime

from data_generator.utils.id_formatter import fmt_assessment

# Fixed creation timestamp shared by all generated assessments.
_CREATED_AT = datetime(2025, 1, 1, 0, 0, 0)

# Due dates spread across a single academic year.
_DUE_AT_START = datetime(2026, 2, 1, 23, 59, 0)
_DUE_AT_END   = datetime(2026, 11, 30, 23, 59, 0)

# Assessment type pool for rng.choice().
_ASSESSMENT_TYPES = ["ASSIGNMENT", "EXAM", "PROJECT", "QUIZ"]

# Discipline prefixes used to generate realistic course codes.
_COURSE_PREFIXES = [
    "CS", "ENG", "BUS", "LAW", "MED",
    "ART", "SCI", "EDU", "PSY", "ECO",
]


def generate_assessments(rng, faker) -> pd.DataFrame:
    """Generate exactly 50 Assessment rows.

    Parameters
    ----------
    rng:
        ``random.Random`` instance seeded externally — used for
        ``assessment_type``, ``course_code``, and ``due_at`` selection.
    faker:
        ``Faker`` instance seeded externally — used for ``title`` values.

    Returns
    -------
    pd.DataFrame
        Columns: assessment_id, title, course_code, assessment_type,
                 due_at, status, created_at
    """
    n = 50
    rows = []

    # Pre-compute equally-spaced due dates across the academic year so
    # the spread is deterministic given the seed.
    start_ts = _DUE_AT_START.timestamp()
    end_ts   = _DUE_AT_END.timestamp()
    step     = (end_ts - start_ts) / (n - 1)

    for i in range(1, n + 1):
        # --- title ----------------------------------------------------------
        # faker.catch_phrase() produces "Innovative scalable framework"
        # style strings that work well as assignment/exam titles.
        title = faker.catch_phrase()

        # --- course_code ----------------------------------------------------
        prefix  = rng.choice(_COURSE_PREFIXES)
        number  = rng.randint(100, 499)
        course_code = f"{prefix}-{number}"

        # --- assessment_type ------------------------------------------------
        assessment_type = rng.choice(_ASSESSMENT_TYPES)

        # --- due_at ---------------------------------------------------------
        # Spread assessments evenly then add a small random jitter (±3 days)
        # so not all due dates fall exactly on the same weekday pattern.
        base_ts  = start_ts + (i - 1) * step
        jitter_s = rng.randint(-3 * 86400, 3 * 86400)
        due_ts   = max(start_ts, min(end_ts, base_ts + jitter_s))
        due_at   = datetime.fromtimestamp(due_ts).replace(hour=23, minute=59, second=0, microsecond=0)

        rows.append({
            "assessment_id":   fmt_assessment(i),
            "title":           title,
            "course_code":     course_code,
            "assessment_type": assessment_type,
            "due_at":          due_at,
            "status":          "ACTIVE",
            "created_at":      _CREATED_AT,
        })

    df = pd.DataFrame(rows, columns=[
        "assessment_id",
        "title",
        "course_code",
        "assessment_type",
        "due_at",
        "status",
        "created_at",
    ])

    # Sanity assertions — catch any logic errors before writing to disk.
    assert len(df) == n, f"Expected {n} Assessment rows, got {len(df)}"
    assert df["assessment_id"].iloc[0] == "ASM-001", "First assessment_id must be ASM-001"
    assert df["assessment_id"].iloc[-1] == "ASM-050", "Last assessment_id must be ASM-050"
    assert df["assessment_type"].isin(_ASSESSMENT_TYPES).all(), \
        "All assessment_type values must be in the allowed enum set"
    assert (df["status"] == "ACTIVE").all(), "All assessments must have status ACTIVE"

    return df
