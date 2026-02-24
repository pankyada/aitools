"""Importance scoring for entities and relationships."""

from __future__ import annotations

import math

MAX_MENTIONS = 1000
HALF_LIFE_DAYS = 30.0
MAX_ACCESS = 500


def compute_importance(
    total_mentions: int,
    recent_mentions: int,
    recency_days: float,
    explicit_boost: float = 0.0,
    access_count: int = 0,
) -> float:
    """Compute bounded importance score in [0.0, 1.0].

    Args:
        total_mentions: Lifetime mentions.
        recent_mentions: Mentions in last 30 days.
        recency_days: Days since last seen.
        explicit_boost: Manual adjustment in [-0.5, 0.5].
        access_count: Retrieval count.

    Returns:
        Final bounded importance score.

    Raises:
        None.
    """

    freq_score = math.log1p(max(total_mentions, 0)) / math.log1p(MAX_MENTIONS)
    recency_score = math.exp(-max(recency_days, 0.0) / HALF_LIFE_DAYS)
    momentum_score = recent_mentions / max(total_mentions, 1)
    access_score = math.log1p(max(access_count, 0)) / math.log1p(MAX_ACCESS)

    weighted = (
        (0.25 * freq_score)
        + (0.30 * recency_score)
        + (0.25 * momentum_score)
        + (0.20 * access_score)
    )
    bounded = max(0.0, min(1.0, weighted + explicit_boost))
    return bounded
