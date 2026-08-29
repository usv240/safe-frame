"""Turn decoded frames into the transition measurements the criteria evaluate.

Everything downstream of this module -- the detector, the ClickHouse criteria
SQL, the anti-join -- operates on `TransitionMetric` rows. This is where those
rows come from: consecutive decoded frames, measured directly in pixel space.

Two measurements are kept deliberately separate for each transition, because
the published criteria test them independently:

    delta   how large the change is *where it happened*, averaged over the
            pixels that actually changed
    area    how much of the screen changed at all

Averaging the delta over the whole frame instead would conflate the two: a
full-brightness flash covering a third of the screen would report a third of
its real luminance step and could slip under the delta floor while comfortably
clearing the area floor. Measuring the step within the changed region and the
extent separately is what lets each floor mean what it says.

Both measurements are taken at full resolution, before any tile aggregation.
`tests/test_spatial_risk.py` shows an 8x8 tile average erasing a 100%
checkerboard reversal completely; that is why `metrics.tile_luminance` is
documented as diagnostic only and is not used here.

Decoding a container into frames is deliberately out of scope: that is
commodity work (ffmpeg, PyAV) and every codec dependency it drags in would sit
in the request path of a service whose job is arithmetic. Callers hand this
module frames they have already decoded.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

import numpy as np

from .metrics import red_difference, red_flash_mask, relative_luminance
from .models import TransitionMetric


def _step_and_area(previous: np.ndarray, current: np.ndarray, threshold: float) -> tuple[float, float, float]:
    """Return (magnitude within the changed region, signed mean, changed area)."""
    delta = current - previous
    changed = np.abs(delta) >= threshold
    area = float(np.mean(changed))
    if not area:
        return 0.0, 0.0, 0.0
    return float(np.mean(np.abs(delta[changed]))), float(np.mean(delta[changed])), area


def frames_to_transitions(
    frames: Iterable[np.ndarray],
    *,
    asset_id: str,
    lineage_id: str,
    parent_id: str = "",
    transform: str = "master",
    frame_rate: float = 25.0,
    first_pts_ms: int = 0,
    luma_threshold: float = 0.1,
    red_threshold: float = 0.1,
) -> Iterator[TransitionMetric]:
    """Measure one transition per consecutive frame pair.

    `frames` are HxWx3 arrays of RGB samples normalised to 0..1. Presentation
    time is derived from `frame_rate`, never from the frame index alone: the
    index is meaningless across a frame-rate conversion, and `pts_ms` is the
    only key the parent/child anti-join can align on.

    Direction is taken from the *signed* mean change within the changed region,
    so a region that brightens while a larger region dims is reported by
    whichever dominates the pixels that actually moved, rather than by a
    whole-frame average that could cancel to zero.
    """
    if frame_rate <= 0:
        raise ValueError("frame_rate must be positive")

    previous_frame: np.ndarray | None = None
    previous_luma: np.ndarray | None = None
    for index, frame in enumerate(frames):
        luma = relative_luminance(frame)
        if previous_frame is not None and previous_luma is not None:
            luma_delta, signed, area = _step_and_area(previous_luma, luma, luma_threshold)

            # The darker of the two states, measured only where the change
            # actually happened. The published general-flash test does not apply
            # when that value is at or above 0.80.
            changed = np.abs(luma - previous_luma) >= luma_threshold
            darker = np.minimum(previous_luma, luma)
            luma_min = float(darker[changed].mean()) if changed.any() else float(darker.mean())

            # The published red test, not a proxy: a pixel counts when at least
            # one state is a saturated red and (R-G-B)x320 swings by more than 20.
            red_pixels = red_flash_mask(previous_frame, frame)
            red_area = float(np.mean(red_pixels))
            red_delta = red_area  # the rule is satisfied per pixel; extent is what varies

            # "Opposing" for the red rule is opposing in *red*, not in luminance.
            # A red/blue alternation at matched luminance has no luminance
            # direction at all, and taking direction from luminance reported it
            # as flat -- which silently disqualified the very case the red rule
            # exists to catch.
            red_signed = 0.0
            if red_pixels.any():
                red_swing = red_difference(frame) - red_difference(previous_frame)
                red_signed = float(red_swing[red_pixels].mean())

            direction = "flat"
            dominant = signed if area >= red_area else red_signed
            if max(area, red_area) and dominant:
                direction = "up" if dominant > 0 else "down"

            yield TransitionMetric(
                asset_id=asset_id,
                lineage_id=lineage_id,
                parent_id=parent_id,
                transform=transform,
                pts_ms=first_pts_ms + int(round(index * 1000 / frame_rate)),
                luma_delta=min(luma_delta, 1.0),
                luma_min=min(max(luma_min, 0.0), 1.0),
                red_delta=min(red_delta, 1.0),
                changed_area_fraction=max(area, red_area),
                direction=direction,
            )
        previous_frame, previous_luma = frame, luma
