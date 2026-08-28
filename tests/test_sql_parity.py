"""The ClickHouse criteria SQL must be a faithful implementation, not a second opinion.

`safe_frame.detector.detect_general_flashes` is the reference implementation of
the published-criteria pre-check. `sql/006_catalogue_regression.sql` re-expresses
that same rule so it can be evaluated across the whole catalogue in one pass.

Two implementations of one safety rule is a real risk: the catalogue sweep could
silently disagree with the per-file detector and nobody would notice. These tests
run both over identical randomized inputs and require exact agreement on whether
a violation exists, which window it starts in, how many transitions it counted,
and the peak changed area.

The SQL half executes through the official read-only `mcp-clickhouse` transport,
so this also exercises the same partner path the product uses at runtime.

Skipped unless MCP_CLICKHOUSE_COMMAND and the ClickHouse connection variables are
configured; CI supplies them from Secret Manager.
"""

from __future__ import annotations

import os
import random

import pytest

from safe_frame.clickhouse_mcp import parity_violations
from safe_frame.detector import detect_general_flashes
from safe_frame.models import TransitionMetric


pytestmark = pytest.mark.skipif(
    not (os.getenv("MCP_CLICKHOUSE_COMMAND") and os.getenv("CLICKHOUSE_HOST")),
    reason="official mcp-clickhouse transport is not configured",
)


def _case(seed: int) -> list[dict[str, object]]:
    """One synthetic asset whose transitions straddle every threshold."""
    rng = random.Random(seed)
    rows: list[dict[str, object]] = []
    pts = 0
    for _ in range(rng.randint(8, 40)):
        pts += rng.choice([40, 80, 100, 120, 150, 250, 400])
        rows.append(
            {
                "asset_id": f"parity_{seed}",
                "pts_ms": pts,
                # straddle the 0.10 luma floor and the 0.25 area floor
                "luma_delta": round(rng.choice([0.0, 0.05, 0.09, 0.10, 0.11, 0.4, 0.8]), 4),
                "changed_area_fraction": round(
                    rng.choice([0.0, 0.1, 0.24, 0.25, 0.26, 0.6, 0.95]), 4
                ),
                "direction": rng.choice(["up", "down", "flat"]),
            }
        )
    return rows


def _reference(rows: list[dict[str, object]]) -> dict[str, object] | None:
    metrics = [
        TransitionMetric(
            asset_id=str(row["asset_id"]),
            lineage_id="parity",
            parent_id="",
            transform="master",
            pts_ms=int(row["pts_ms"]),
            luma_delta=float(row["luma_delta"]),
            red_delta=0.0,
            changed_area_fraction=float(row["changed_area_fraction"]),
            direction=str(row["direction"]),
        )
        for row in rows
    ]
    found = detect_general_flashes(metrics)
    if not found:
        return None
    violation = found[0]
    return {
        "asset_id": violation.asset_id,
        "window_start_ms": violation.window_start_ms,
        "window_end_ms": violation.window_end_ms,
        "transitions": violation.transitions,
        "peak_changed_area_fraction": round(violation.peak_changed_area_fraction, 6),
    }


def _normalise(row: dict[str, object]) -> dict[str, object]:
    return {
        "asset_id": str(row["asset_id"]),
        "window_start_ms": int(row["window_start_ms"]),
        "window_end_ms": int(row["window_end_ms"]),
        "transitions": int(row["transitions"]),
        "peak_changed_area_fraction": round(float(row["peak_changed_area_fraction"]), 6),
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("seed", range(40))
async def test_sql_matches_reference_detector(seed: int) -> None:
    rows = _case(seed)
    expected = _reference(rows)
    returned = await parity_violations(rows)
    actual = _normalise(returned[0]) if returned else None
    assert actual == expected, (
        f"seed {seed}: ClickHouse criteria SQL disagreed with the reference detector.\n"
        f"  python:     {expected}\n"
        f"  clickhouse: {actual}"
    )


@pytest.mark.asyncio
async def test_boundary_of_six_transitions_agrees() -> None:
    """Exactly six opposing transitions must pass in both implementations."""
    for count, should_violate in ((6, False), (7, True)):
        rows = [
            {
                "asset_id": f"boundary_{count}",
                "pts_ms": index * 100,
                "luma_delta": 0.8,
                "changed_area_fraction": 0.9,
                "direction": "up" if index % 2 == 0 else "down",
            }
            for index in range(count)
        ]
        expected = _reference(rows)
        returned = await parity_violations(rows)
        assert (expected is not None) is should_violate
        assert (len(returned) > 0) is should_violate
        if should_violate:
            assert _normalise(returned[0]) == expected


@pytest.mark.asyncio
async def test_same_direction_burst_agrees_on_pass() -> None:
    """A fast burst that never reverses is not a general flash in either implementation."""
    rows = [
        {
            "asset_id": "same_direction",
            "pts_ms": index * 100,
            "luma_delta": 0.8,
            "changed_area_fraction": 0.9,
            "direction": "up",
        }
        for index in range(10)
    ]
    assert _reference(rows) is None
    assert await parity_violations(rows) == []
