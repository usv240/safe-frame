from __future__ import annotations

from collections.abc import Callable, Sequence

from .models import TransitionMetric, Violation


# Published photosensitivity guidance defines more than one flash rule, and a
# sequence can satisfy one while staying clear of the other. The general-flash
# rule is driven by luminance change; the red-flash rule is driven by change in
# saturated red and deliberately carries **no luminance floor**, because a
# red/blue alternation at near-constant luminance is exactly the case a
# luminance-only detector misses. Both are evaluated; the anti-join is already
# keyed on `rule`, so a rendition that introduces either is isolated.
GENERAL_LUMA_FLOOR = 0.10
# "where the relative luminance of the darker image is below 0.80" -- a swing
# between two bright images is not a general flash, however large it is.
DARKER_IMAGE_CEILING = 0.80
RED_DELTA_FLOOR = 0.20
AREA_FLOOR = 0.25
MAX_TRANSITIONS_PER_SECOND = 6


def _window_violations(
    metrics: Sequence[TransitionMetric],
    *,
    rule: str,
    qualifies: Callable[[TransitionMetric], bool],
    max_transitions_per_second: int,
) -> list[Violation]:
    """More than `max_transitions_per_second` opposing qualifying pairs in 1000 ms.

    A window is anchored on a qualifying transition, never on a sample that does
    not itself count toward the criterion. `sql/006_catalogue_regression.sql`
    anchors identically; tests/test_sql_parity.py asserts the two agree.
    """
    qualified = [item for item in sorted(metrics, key=lambda item: item.pts_ms) if qualifies(item)]
    for index, start in enumerate(qualified):
        window = [item for item in qualified[index:] if item.pts_ms < start.pts_ms + 1_000]
        if len(window) <= max_transitions_per_second:
            continue
        if {item.direction for item in window} != {"up", "down"}:
            continue
        # Report one canonical window for a continuous burst.
        return [
            Violation(
                asset_id=start.asset_id,
                lineage_id=start.lineage_id,
                parent_id=start.parent_id,
                transform=start.transform,
                window_start_ms=start.pts_ms,
                window_end_ms=start.pts_ms + 1_000,
                rule=rule,
                transitions=len(window),
                peak_changed_area_fraction=max(item.changed_area_fraction for item in window),
            )
        ]
    return []


def detect_general_flashes(
    metrics: Sequence[TransitionMetric],
    *,
    max_transitions_per_second: int = MAX_TRANSITIONS_PER_SECOND,
    luma_delta_floor: float = GENERAL_LUMA_FLOOR,
    area_floor: float = AREA_FLOOR,
    darker_image_ceiling: float = DARKER_IMAGE_CEILING,
) -> list[Violation]:
    """Detect more than three opposing luminance flash pairs in a rolling second.

    Three conditions, all from the published definition: the luminance change is
    at least 10% of maximum, the darker of the two states is below 0.80 relative
    luminance, and the affected area clears the area floor.

    This is an open pre-check, not a certified implementation. Thresholds are
    explicit and independently testable.
    """
    return _window_violations(
        metrics,
        rule="general_flash",
        qualifies=lambda item: (
            item.luma_delta >= luma_delta_floor
            and item.luma_min < darker_image_ceiling
            and item.changed_area_fraction >= area_floor
            and item.direction != "flat"
        ),
        max_transitions_per_second=max_transitions_per_second,
    )


def detect_red_flashes(
    metrics: Sequence[TransitionMetric],
    *,
    max_transitions_per_second: int = MAX_TRANSITIONS_PER_SECOND,
    red_delta_floor: float = RED_DELTA_FLOOR,
    area_floor: float = AREA_FLOOR,
) -> list[Violation]:
    """Detect opposing transitions to or from saturated red, at any luminance.

    There is no luminance floor here on purpose. A saturated-red alternation can
    hold luminance almost flat and still be the higher-risk sequence, so gating
    it on `luma_delta` would reproduce the blind spot this rule exists to close.
    """
    return _window_violations(
        metrics,
        rule="red_flash",
        qualifies=lambda item: (
            item.red_delta >= red_delta_floor
            and item.changed_area_fraction >= area_floor
            and item.direction != "flat"
        ),
        max_transitions_per_second=max_transitions_per_second,
    )


def detect_violations(metrics: Sequence[TransitionMetric]) -> list[Violation]:
    """Every implemented rule, ordered so a reader sees the rule that fired."""
    return [*detect_general_flashes(metrics), *detect_red_flashes(metrics)]
