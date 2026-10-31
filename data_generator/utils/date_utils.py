"""
Chronological date helpers for the Academic Integrity data generator.

All functions accept a ``random.Random`` instance as their first argument.
No function creates its own random source — all randomness flows through
the shared ``rng`` passed in from ``main.py``.
"""

import random
from datetime import datetime, timedelta


def random_datetime(rng: random.Random, start: datetime, end: datetime) -> datetime:
    """Return a random datetime between *start* and *end* inclusive.

    Args:
        rng:   A ``random.Random`` instance (the shared generator RNG).
        start: The earliest allowable datetime (inclusive).
        end:   The latest allowable datetime (inclusive).

    Returns:
        A ``datetime`` uniformly chosen from the half-open interval
        [start, end].  When *start* == *end* the function returns *start*.

    Raises:
        ValueError: If *end* is before *start*.
    """
    if end < start:
        raise ValueError(f"end ({end!r}) must not be before start ({start!r})")

    delta_seconds = int((end - start).total_seconds())
    if delta_seconds == 0:
        return start

    offset_seconds = rng.randint(0, delta_seconds)
    return start + timedelta(seconds=offset_seconds)


def ascending_timestamps(
    rng: random.Random,
    base: datetime,
    n: int,
    max_gap_days: int,
) -> list[datetime]:
    """Return a list of *n* strictly ascending datetimes.

    Each timestamp is ``base + accumulated_delta`` where each individual
    delta is ``rng.randint(1, max_gap_days)`` days.  Because every delta
    is at least 1 day the resulting list is guaranteed to be strictly
    ascending.

    Args:
        rng:          A ``random.Random`` instance (the shared generator RNG).
        base:         The anchor datetime; the first returned timestamp is
                      ``base + delta_1`` (i.e. *base* itself is NOT included).
        n:            The number of timestamps to generate.  Must be >= 0.
        max_gap_days: The maximum day gap between consecutive timestamps.
                      Must be >= 1.

    Returns:
        A list of *n* ``datetime`` objects in strictly ascending order.
        Returns an empty list when *n* == 0.

    Raises:
        ValueError: If *n* < 0 or *max_gap_days* < 1.
    """
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    if max_gap_days < 1:
        raise ValueError(f"max_gap_days must be >= 1, got {max_gap_days}")

    timestamps: list[datetime] = []
    current = base
    for _ in range(n):
        delta = rng.randint(1, max_gap_days)
        current = current + timedelta(days=delta)
        timestamps.append(current)

    return timestamps
