"""
Generator for Reviewer reference data.

Produces exactly 30 Reviewer rows with unique email addresses, realistic
names, and roles distributed across the three permitted enum values.
All columns match the `Reviewer` table defined in database/schema.sql.
"""

import pandas as pd
from datetime import datetime

from data_generator.utils.id_formatter import fmt_reviewer

# Fixed creation timestamp shared by all generated reviewers.
_CREATED_AT = datetime(2025, 1, 1, 0, 0, 0)

# Permitted reviewer roles (must match ENUM in schema.sql).
_REVIEWER_ROLES = ["INSTRUCTOR", "ACADEMIC_ADMIN", "REVIEWER"]


def generate_reviewers(rng, faker) -> pd.DataFrame:
    """Generate exactly 30 Reviewer rows.

    Parameters
    ----------
    rng:
        ``random.Random`` instance seeded externally — used for
        ``reviewer_role`` selection.
    faker:
        ``Faker`` instance seeded externally — used for full names and
        email addresses.

    Returns
    -------
    pd.DataFrame
        Columns: reviewer_id, full_name, email, reviewer_role, status,
                 created_at
    """
    n = 30
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

        # --- reviewer_role -----------------------------------------------
        reviewer_role = rng.choice(_REVIEWER_ROLES)

        rows.append({
            "reviewer_id":   fmt_reviewer(i),
            "full_name":     full_name,
            "email":         email,
            "reviewer_role": reviewer_role,
            "status":        "ACTIVE",
            "created_at":    _CREATED_AT,
        })

    df = pd.DataFrame(rows, columns=[
        "reviewer_id",
        "full_name",
        "email",
        "reviewer_role",
        "status",
        "created_at",
    ])

    # Sanity assertions — catch any logic errors before writing to disk.
    assert len(df) == n, f"Expected {n} Reviewer rows, got {len(df)}"
    assert df["reviewer_id"].iloc[0] == "REV-001", "First reviewer_id must be REV-001"
    assert df["reviewer_id"].iloc[-1] == "REV-030", "Last reviewer_id must be REV-030"
    assert df["email"].nunique() == n, "All email addresses must be unique"
    assert df["reviewer_role"].isin(_REVIEWER_ROLES).all(), \
        "All reviewer_role values must be INSTRUCTOR, ACADEMIC_ADMIN, or REVIEWER"
    assert (df["status"] == "ACTIVE").all(), "All reviewers must have status ACTIVE"

    return df
