"""Close the loop from pixels to verdict.

Every other test starts from `TransitionMetric` rows. These start from RGB
frames, so the measurement stage is held to the same standard as the criteria
stage: constructed frame sequences with a known answer, run through the real
measurement and the real detector.

No frame sequence here is rendered or displayed anywhere; they are numpy arrays
used as test input.
"""

from __future__ import annotations

import numpy as np

from safe_frame.detector import detect_general_flashes, detect_red_flashes, detect_violations
from safe_frame.ingest import frames_to_transitions


def solid(rgb: tuple[float, float, float], size: int = 32) -> np.ndarray:
    return np.tile(np.array(rgb, dtype=float), (size, size, 1))


def alternating(a: np.ndarray, b: np.ndarray, count: int) -> list[np.ndarray]:
    return [a if index % 2 == 0 else b for index in range(count)]


def measure(frames, **kwargs):
    return list(
        frames_to_transitions(
            frames, asset_id="child", lineage_id="tree", parent_id="master",
            transform="test", frame_rate=25.0, **kwargs
        )
    )


def test_presentation_time_comes_from_the_frame_rate_not_the_index():
    """Frame index is not a lineage key; two rates must land on the same pts."""
    frames = alternating(solid((0.0, 0.0, 0.0)), solid((1.0, 1.0, 1.0)), 6)
    at_25 = [item.pts_ms for item in measure(frames)]
    at_50 = [
        item.pts_ms
        for item in frames_to_transitions(
            alternating(solid((0.0, 0.0, 0.0)), solid((1.0, 1.0, 1.0)), 11),
            asset_id="child", lineage_id="tree", frame_rate=50.0,
        )
    ]
    # a transition is timestamped at the frame the change arrives on, so the
    # first transition is at 40 ms rather than 0
    assert at_25 == [40, 80, 120, 160, 200]
    # the 50 fps rendition has twice the frames but shares every pts of the 25 fps one
    assert set(at_25).issubset(set(at_50))


def test_full_screen_luminance_alternation_is_measured_and_flagged():
    metrics = measure(alternating(solid((0.05, 0.05, 0.05)), solid((0.95, 0.95, 0.95)), 9))
    assert len(metrics) == 8
    assert all(item.changed_area_fraction == 1.0 for item in metrics)
    assert all(item.luma_delta > 0.85 for item in metrics)
    assert {item.direction for item in metrics} == {"up", "down"}
    assert [item.rule for item in detect_violations(metrics)] == ["general_flash"]


def test_red_alternation_at_matched_luminance_is_caught_only_by_the_red_rule():
    """The blind spot, demonstrated from pixels rather than from hand-written metrics.

    Saturated red and a blue-green of the same BT.709 luminance alternate, so
    relative luminance barely moves while saturated red swings the full range.
    A luminance-only checker sees nothing here.
    """
    red = solid((1.0, 0.0, 0.0))
    # 0.2126 is red's BT.709 weight; match it with green+blue so luma is equal
    match = 0.2126 / (0.7152 + 0.0722)
    teal = solid((0.0, match, match))
    metrics = measure(alternating(red, teal, 9))

    luma_swing = max(item.luma_delta for item in metrics)
    red_swing = max(item.red_delta for item in metrics)
    assert luma_swing < 0.01, f"luminance should be near-flat, got {luma_swing}"
    assert red_swing > 0.9, f"saturated red should swing, got {red_swing}"

    assert detect_general_flashes(metrics) == []
    assert len(detect_red_flashes(metrics)) == 1
    assert [item.rule for item in detect_violations(metrics)] == ["red_flash"]


def test_a_small_flashing_region_does_not_reach_the_area_floor():
    dark, bright = solid((0.05, 0.05, 0.05)), solid((0.05, 0.05, 0.05)).copy()
    bright[:4, :4] = 0.95  # 16 of 1024 pixels, well under the 0.25 area floor
    metrics = measure(alternating(dark, bright, 9))
    assert all(item.changed_area_fraction < 0.02 for item in metrics)
    # the step where it happened is still large; only the area disqualifies it
    assert all(item.luma_delta > 0.85 for item in metrics)
    assert detect_violations(metrics) == []


def test_the_step_is_measured_where_it_happened_not_averaged_over_the_frame():
    """Half-screen full-range flash keeps its real luminance step.

    A whole-frame mean would report ~0.45 here and could fall under a stricter
    delta floor while the area floor was comfortably met. The two measurements
    must stay independent.
    """
    dark, half = solid((0.05, 0.05, 0.05)), solid((0.05, 0.05, 0.05)).copy()
    half[:16] = 0.95
    metrics = measure(alternating(dark, half, 9))
    assert all(abs(item.changed_area_fraction - 0.5) < 1e-9 for item in metrics)
    assert all(item.luma_delta > 0.85 for item in metrics)
    assert [item.rule for item in detect_violations(metrics)] == ["general_flash"]


def test_a_static_sequence_produces_flat_transitions_and_no_violation():
    metrics = measure([solid((0.4, 0.4, 0.4)) for _ in range(9)])
    assert all(item.direction == "flat" for item in metrics)
    assert all(item.changed_area_fraction == 0.0 for item in metrics)
    assert detect_violations(metrics) == []


def test_measured_metrics_survive_the_wire_contract():
    """What ingest produces must be exactly what /v1/scan accepts."""
    metrics = measure(alternating(solid((0.05, 0.05, 0.05)), solid((0.95, 0.95, 0.95)), 4))
    for item in metrics:
        payload = item.model_dump()
        assert set(payload) == {
            "asset_id", "lineage_id", "parent_id", "transform", "pts_ms",
            "luma_delta", "red_delta", "changed_area_fraction", "direction",
        }
        assert 0.0 <= payload["luma_delta"] <= 1.0
        assert 0.0 <= payload["red_delta"] <= 1.0
        assert 0.0 <= payload["changed_area_fraction"] <= 1.0
