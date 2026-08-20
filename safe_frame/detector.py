from __future__ import annotations

from collections.abc import Sequence

from .models import TransitionMetric, Violation


def detect_general_flashes(
    metrics: Sequence[TransitionMetric],
    *,
    max_transitions_per_second: int = 6,
    luma_delta_floor: float = 0.1,
    area_floor: float = 0.25,
) -> list[Violation]:
    """Detect more than three opposing flash pairs in a rolling second.

    This is an open pre-check, not a certified implementation of ITU-R BT.1702.
    Thresholds are explicit and independently testable.
    """
    ordered = sorted(metrics, key=lambda item: item.pts_ms)
    violations: list[Violation] = []
    for index, start in enumerate(ordered):
        window = [
            item
            for item in ordered[index:]
            if item.pts_ms < start.pts_ms + 1_000
            and item.luma_delta >= luma_delta_floor
            and item.changed_area_fraction >= area_floor
            and item.direction != "flat"
        ]
        if len(window) <= max_transitions_per_second:
            continue
        directions = {item.direction for item in window}
        if directions != {"up", "down"}:
            continue
        violations.append(
            Violation(
                asset_id=start.asset_id,
                lineage_id=start.lineage_id,
                parent_id=start.parent_id,
                transform=start.transform,
                window_start_ms=start.pts_ms,
                window_end_ms=start.pts_ms + 1_000,
                rule="general_flash",
                transitions=len(window),
                peak_changed_area_fraction=max(item.changed_area_fraction for item in window),
            )
        )
        # Report one canonical window for a continuous burst.
        break
    return violations
