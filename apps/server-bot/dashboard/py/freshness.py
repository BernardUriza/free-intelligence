"""Data-age classification — the dashboard's only liveness signal that can go red.

An HTTP 200 from a static blob proves the blob exists, never that anything is
still writing it. Every liveness claim this dashboard makes is derived here,
from the producer's own timestamp inside the payload.
"""

import time

from py.config import FRESH_MAX_AGE_SECONDS, STALE_MAX_AGE_SECONDS

FRESH = "fresh"
STALE = "stale"
DEAD = "dead"
UNDATED = "undated"
UNREACHABLE = "unreachable"

PILL_CLASS = {
    FRESH: "live",
    STALE: "stale",
    DEAD: "dead",
    UNDATED: "stale",
    UNREACHABLE: "error",
}


def age_of(produced_at):
    if not produced_at:
        return None
    return max(0.0, time.time() - produced_at)


def classify(age):
    if age is None:
        return UNDATED
    if age <= FRESH_MAX_AGE_SECONDS:
        return FRESH
    if age <= STALE_MAX_AGE_SECONDS:
        return STALE
    return DEAD


def is_trustworthy(state):
    return state == FRESH
