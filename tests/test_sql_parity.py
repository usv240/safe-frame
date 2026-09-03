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

These tests execute real SQL, so they are skipped unless MCP_CLICKHOUSE_COMMAND
and the ClickHouse connection variables point at a reachable cluster. The
`parity` CI job stands up a throwaway ClickHouse and runs them through the real
official mcp-clickhouse transport on every commit, and fails if they skip -- for
most of this project's life they skipped everywhere anyone could look, which hid
a defect in the comparison below that meant they had never once executed.
"""

from __future__ import annotations

import os
import random

import pytest

from safe_frame.clickhouse_mcp import parity_violations
from safe_frame.detector import detect_violations
from safe_frame.models import TransitionMetric


# Applied per test rather than to the module: the fixture-strength check below
# needs no cluster and must run in CI, or a fixture that stops producing
# violations would silently weaken every parity assertion here.
requires_cluster = pytest.mark.skipif(
    not (os.getenv("MCP_CLICKHOUSE_COMMAND") and os.getenv("CLICKHOUSE_HOST")),
    reason="official mcp-clickhouse transport is not configured",
)


def _case(seed: int) -> list[dict[str, object]]:
    """One synthetic asset whose transitions straddle every threshold.

    Spacing is drawn per case rather than per row. Sparse cases (200-400 ms
    apart) can never fit seven qualifying transitions into a second and must
    agree on "no violation"; dense cases (40-120 ms apart) routinely do fire.
    Without the dense band the suite would only ever prove the two
    implementations agree about nothing, which is not the claim being made --
    `test_fixtures_exercise_both_rules` fails if that regresses.
    """
    rng = random.Random(seed)
    spacing = rng.choice([[40, 60, 80], [80, 100, 120], [100, 150, 250], [250, 400]])
    rows: list[dict[str, object]] = []
    pts = 0
    for _ in range(rng.randint(8, 40)):
        pts += rng.choice(spacing)
        rows.append(
            {
                "asset_id": f"parity_{seed}",
                "pts_ms": pts,
                # straddle the 0.10 luma floor and the 0.25 area floor
                "luma_delta": round(rng.choice([0.0, 0.05, 0.09, 0.10, 0.11, 0.4, 0.8, 0.8]), 4),
                # straddle the 0.80 darker-image ceiling, so cases arise where a
                # large luminance swing is correctly NOT a general flash
                # weighted toward dark, as content is: the ceiling should bite
                # sometimes, not dominate, or the general rule stops being tested
                "luma_min": round(rng.choice([0.0, 0.02, 0.05, 0.1, 0.1, 0.2, 0.79, 0.90]), 4),
                # straddle the 0.20 red floor independently, so cases arise where
                # one rule fires and the other does not
                "red_delta": round(rng.choice([0.0, 0.05, 0.19, 0.20, 0.21, 0.5, 0.9, 0.9]), 4),
                "changed_area_fraction": round(
                    rng.choice([0.0, 0.1, 0.24, 0.25, 0.26, 0.6, 0.95, 0.95]), 4
                ),
                "direction": rng.choice(["up", "down", "up", "down", "flat"]),
            }
        )
    return rows


def test_fixtures_exercise_both_rules() -> None:
    """Agreement is only evidence if the fixtures actually trip the criteria.

    Needs no cluster -- it checks the reference detector alone -- so it samples a
    wider seed range than the parametrised tests can afford in cluster
    round-trips. A fixture change that quietly stops producing violations fails
    here rather than silently weakening every parity assertion above.

    Each rule now carries four independent conditions, so the joint probability
    of a randomly drawn second satisfying all of them more than six times is
    genuinely low. The sample is widened rather than the floor lowered.
    """
    fired: dict[str, int] = {}
    ceiling_excluded = 0
    for seed in range(200):
        rows = _case(seed)
        for violation in _reference(rows):
            fired[str(violation["rule"])] = fired.get(str(violation["rule"]), 0) + 1
        ceiling_excluded += sum(
            1 for row in rows
            if float(row["luma_min"]) >= 0.80 and float(row["luma_delta"]) >= 0.10
        )
    assert fired.get("general_flash", 0) >= 10, f"general_flash barely fires: {fired}"
    assert fired.get("red_flash", 0) >= 10, f"red_flash barely fires: {fired}"
    # and the darker-image ceiling must actually be exercised, not just present
    assert ceiling_excluded >= 50, "the fixtures never test the darker-image ceiling"


def _reference(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    metrics = [
        TransitionMetric(
            asset_id=str(row["asset_id"]),
            lineage_id="parity",
            parent_id="",
            transform="master",
            pts_ms=int(row["pts_ms"]),
            luma_delta=float(row["luma_delta"]),
            luma_min=float(row.get("luma_min", 0.0)),
            red_delta=float(row.get("red_delta", 0.0)),
            changed_area_fraction=float(row["changed_area_fraction"]),
            direction=str(row["direction"]),
        )
        for row in rows
    ]
    return sorted(
        (
            {
                "asset_id": violation.asset_id,
                "rule": violation.rule,
                "window_start_ms": violation.window_start_ms,
                "window_end_ms": violation.window_end_ms,
                "transitions": violation.transitions,
                "peak_changed_area_fraction": round(violation.peak_changed_area_fraction, 6),
            }
            for violation in detect_violations(metrics)
        ),
        key=lambda item: (item["asset_id"], item["rule"]),
    )


def _normalise(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        (
            {
                "asset_id": str(row["asset_id"]),
                "rule": str(row["rule"]),
                "window_start_ms": int(row["window_start_ms"]),
                "window_end_ms": int(row["window_end_ms"]),
                "transitions": int(row["transitions"]),
                "peak_changed_area_fraction": round(float(row["peak_changed_area_fraction"]), 6),
            }
            for row in rows
        ),
        key=lambda item: (item["asset_id"], item["rule"]),
    )


@requires_cluster
@pytest.mark.asyncio
@pytest.mark.parametrize("seed", range(40))
async def test_sql_matches_reference_detector(seed: int) -> None:
    rows = _case(seed)
    expected = _reference(rows)
    returned = await parity_violations(rows)
    actual = _normalise(returned)
    assert actual == expected, (
        f"seed {seed}: ClickHouse criteria SQL disagreed with the reference detector.\n"
        f"  python:     {expected}\n"
        f"  clickhouse: {actual}"
    )


@requires_cluster
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
        actual = _normalise(await parity_violations(rows))
        assert (len(expected) > 0) is should_violate
        assert actual == expected


@requires_cluster
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
    assert _reference(rows) == []
    assert await parity_violations(rows) == []


@requires_cluster
@pytest.mark.asyncio
async def test_red_flash_fires_where_general_flash_cannot() -> None:
    """The case a luminance-only detector passes, agreed by both implementations.

    Luminance change is held at 0.04, below the 0.10 general-flash floor, while
    saturated red alternates well above the 0.20 red floor. `general_flash` must
    stay silent and `red_flash` must fire, in Python and in ClickHouse alike.
    """
    rows = [
        {
            "asset_id": "red_only",
            "pts_ms": index * 100,
            "luma_delta": 0.04,
            "red_delta": 0.55,
            "changed_area_fraction": 0.8,
            "direction": "up" if index % 2 == 0 else "down",
        }
        for index in range(9)
    ]
    expected = _reference(rows)
    assert [item["rule"] for item in expected] == ["red_flash"], (
        "a red alternation under the luminance floor must be caught only by the red rule"
    )
    assert _normalise(await parity_violations(rows)) == expected


@requires_cluster
@pytest.mark.asyncio
async def test_rules_are_windowed_independently() -> None:
    """One rule's qualifying transitions must not pad the other rule's window.

    Four red-only transitions followed by four luminance-only transitions is
    eight qualifying transitions inside one second, but neither rule reaches
    seven on its own, so nothing may be reported.
    """
    red = [
        {
            "asset_id": "independent",
            "pts_ms": index * 100,
            "luma_delta": 0.04,
            "red_delta": 0.55,
            "changed_area_fraction": 0.8,
            "direction": "up" if index % 2 == 0 else "down",
        }
        for index in range(4)
    ]
    luma = [
        {
            "asset_id": "independent",
            "pts_ms": 400 + index * 100,
            "luma_delta": 0.8,
            "red_delta": 0.01,
            "changed_area_fraction": 0.8,
            "direction": "up" if index % 2 == 0 else "down",
        }
        for index in range(4)
    ]
    rows = red + luma
    assert _reference(rows) == []
    assert await parity_violations(rows) == []


@requires_cluster
@pytest.mark.asyncio
async def test_darker_image_ceiling_agrees() -> None:
    """A bright-on-bright alternation is not a general flash, in both implementations.

    Every other condition is met: the delta clears 0.10, the area clears 0.25,
    the directions oppose, and there are more than six of them in a second. Only
    the darker image is above 0.80. The published test does not apply, and
    neither implementation may report it.
    """
    for luma_min, should_violate in ((0.79, True), (0.80, False), (0.95, False)):
        rows = [
            {
                "asset_id": f"ceiling_{int(luma_min * 100)}",
                "pts_ms": index * 100,
                "luma_delta": 0.5,
                "luma_min": luma_min,
                "red_delta": 0.0,
                "changed_area_fraction": 0.9,
                "direction": "up" if index % 2 == 0 else "down",
            }
            for index in range(9)
        ]
        expected = _reference(rows)
        assert (len(expected) > 0) is should_violate, f"python disagreed at {luma_min}"
        assert _normalise(await parity_violations(rows)) == expected
