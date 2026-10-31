"""
Generator for Learner reference data.

Produces exactly 500 Learner rows with unique email addresses, realistic
names, a year_of_study in the range 1–10, and a program drawn from a
curated list of academic disciplines.  All columns match the `Learner`
table defined in database/schema.sql.
"""

import pandas as pd
from datetime import datetime

from data_generator.utils.id_formatter import fmt_learner

# Fixed creation timestamp shared by all generated learners.
_CREATED_AT = datetime(2025, 1, 1, 0, 0, 0)

# Curated list of academic programmes.
_PROGRAMS = [
    "Computer Science",
    "Engineering",
    "Business",
    "Law",
    "Medicine",
    "Arts",
    "Science",
    "Education",
    "Psychology",
    "Economics",
]


def generate_learners(rng, nprng, faker) -> pd.DataFrame:
    """Generate exactly 500 Learner rows.

    Parameters
    ----------
    rng:
        ``random.Random`` instance seeded externally — used for
        ``year_of_study`` selection and programme choice.
    nprng:
        ``numpy.random.Generator`` instance seeded externally — available
        for callers that need NumPy distributions; not used internally so
        that NumPy state is not consumed unnecessarily.
    faker:
        ``Faker`` instance seeded externally — used for full names and
        email addresses.

    Returns
    -------
    pd.DataFrame
        Columns: learner_id, full_name, email, program, year_of_study,
                 status, created_at
    """
    n = 500
    rows = []
    seen_emails: set[str] = set()

    for i in range(1, n + 1):
        # --- full_name ---------------------------------------------------
        full_name = faker.name()

        # --- email (must be unique within the table) ----------------------
        email = faker.email()
        while email in seen_emails:
            email = faker.email()
        seen_emails.add(email)

        # --- year_of_study ------------------------------------------------
        # rng.randint(a, b) is inclusive on both ends for random.Random.
        year_of_study = rng.randint(1, 10)

        # --- program -------------------------------------------------------
        program = rng.choice(_PROGRAMS)

        rows.append({
            "learner_id":    fmt_learner(i),
            "full_name":     full_name,
            "email":         email,
            "program":       program,
            "year_of_study": year_of_study,
            "status":        "ACTIVE",
            "created_at":    _CREATED_AT,
        })

    df = pd.DataFrame(rows, columns=[
        "learner_id",
        "full_name",
        "email",
        "program",
        "year_of_study",
        "status",
        "created_at",
    ])

    # Sanity assertions — catch any logic errors before writing to disk.
    assert len(df) == n, f"Expected {n} Learner rows, got {len(df)}"
    assert df["learner_id"].iloc[0] == "LRN-001", "First learner_id must be LRN-001"
    assert df["learner_id"].iloc[-1] == "LRN-500", "Last learner_id must be LRN-500"
    assert df["email"].nunique() == n, "All email addresses must be unique"
    assert df["year_of_study"].between(1, 10).all(), "year_of_study must be in range 1–10"
    assert (df["status"] == "ACTIVE").all(), "All learners must have status ACTIVE"

    return df
