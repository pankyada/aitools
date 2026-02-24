"""Tests for importance scoring behavior."""

from __future__ import annotations

from ait_memory.importance import compute_importance


def test_importance_increases_with_mentions() -> None:
    """Higher mention count should increase score, all else equal."""

    low = compute_importance(total_mentions=1, recent_mentions=1, recency_days=1.0)
    high = compute_importance(total_mentions=100, recent_mentions=50, recency_days=1.0)
    assert high > low


def test_importance_clamped_bounds() -> None:
    """Score should stay within [0, 1]."""

    score = compute_importance(
        total_mentions=10_000,
        recent_mentions=10_000,
        recency_days=0,
        explicit_boost=1.0,
        access_count=10_000,
    )
    assert 0.0 <= score <= 1.0
