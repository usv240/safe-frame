"""Measure frames a visitor supplied, using the same path the catalogue used.

The catalogue demonstrates the product on content we chose. The fair objection
is that we chose it. This module lets someone bring their own clip and get the
same verdict from the same code.

Two decisions matter here.

**The browser decodes, the server measures.** Reimplementing the published
maths in JavaScript would create a third implementation of one safety rule, and
`tests/test_sql_parity.py` exists precisely because two are already a risk. So
the page decodes video to raw RGB and posts the samples; every luminance and
red-difference number still comes out of `safe_frame.ingest`, the function the
measured cohort and the test suite already exercise.

**Frames arrive downscaled, and that is disclosed.** A 1920x1080 clip at 25fps
is 150MB of samples per second of video. The page reduces each frame to a small
grid before sending. This is well matched to what the criteria actually ask:
the area condition is a *proportion of the screen* (0.25), not a pixel count, so
a grid of a few hundred cells resolves it comfortably. It is not well matched to
a flash occupying a very small part of the frame, which is exactly the case the
area condition excludes anyway. `AREA_RESOLUTION_NOTE` states this on the
result, because a screening tool that hides its own resolution limit is worse
than one that has none.
"""

from __future__ import annotations

import base64
import binascii
from typing import Iterator

import numpy as np

from .ingest import frames_to_transitions
from .models import TransitionMetric


# A frame grid must resolve the 0.25 area condition and nothing finer. 64x64 is
# far more than that needs and keeps a 900-frame clip inside a few megabytes.
MAX_WIDTH = 64
MAX_HEIGHT = 64
MAX_FRAMES = 900
MIN_FRAMES = 2
MAX_FRAME_RATE = 240.0
MIN_FRAME_RATE = 1.0

AREA_RESOLUTION_NOTE = (
    "Frames were reduced to a {width}x{height} grid in your browser before measurement. "
    "The published area condition is a proportion of the screen (0.25), which a grid this "
    "size resolves; a flash covering a very small part of the frame may be attenuated, and "
    "such a flash does not meet the area condition in the first place."
)


class FrameDecodeError(ValueError):
    """The submitted frame buffer does not match its declared shape."""


def decode_frames(
    frames_b64: str, *, width: int, height: int, frame_count: int
) -> Iterator[np.ndarray]:
    """Decode base64 RGB samples into the HxWx3 float arrays ingest expects.

    Validated strictly rather than trusted: the declared shape and the actual
    byte length must agree exactly, so a truncated upload fails loudly instead
    of being measured as a shorter clip and silently passing.
    """
    if not (1 <= width <= MAX_WIDTH and 1 <= height <= MAX_HEIGHT):
        raise FrameDecodeError(
            f"frame grid must be within {MAX_WIDTH}x{MAX_HEIGHT}, got {width}x{height}"
        )
    if not (MIN_FRAMES <= frame_count <= MAX_FRAMES):
        raise FrameDecodeError(
            f"frame_count must be between {MIN_FRAMES} and {MAX_FRAMES}, got {frame_count}"
        )
    try:
        raw = base64.b64decode(frames_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise FrameDecodeError("frames_b64 is not valid base64") from exc

    expected = frame_count * height * width * 3
    if len(raw) != expected:
        raise FrameDecodeError(
            f"frame buffer is {len(raw)} bytes but {frame_count} frames of "
            f"{width}x{height} RGB require {expected}"
        )

    samples = np.frombuffer(raw, dtype=np.uint8).reshape(frame_count, height, width, 3)
    for frame in samples:
        yield frame.astype(np.float32) / 255.0


def measure_clip(
    frames_b64: str,
    *,
    width: int,
    height: int,
    frame_count: int,
    frame_rate: float,
    asset_id: str,
    lineage_id: str,
    parent_id: str = "",
    transform: str = "master",
) -> list[TransitionMetric]:
    """Run submitted frames through the product's own measurement stage."""
    if not (MIN_FRAME_RATE <= frame_rate <= MAX_FRAME_RATE):
        raise FrameDecodeError(
            f"frame_rate must be between {MIN_FRAME_RATE} and {MAX_FRAME_RATE}, got {frame_rate}"
        )
    frames = decode_frames(
        frames_b64, width=width, height=height, frame_count=frame_count
    )
    return list(
        frames_to_transitions(
            frames,
            asset_id=asset_id,
            lineage_id=lineage_id,
            parent_id=parent_id,
            transform=transform,
            frame_rate=frame_rate,
        )
    )


def per_second_counts(metrics: list[TransitionMetric]) -> list[dict[str, object]]:
    """Qualifying transitions per second, for the same chart the catalogue draws.

    Counts the transitions that actually meet each rule's conditions, so the
    chart shows what the criteria saw rather than raw frame differences.
    """
    buckets: dict[int, dict[str, int]] = {}
    for metric in metrics:
        second = metric.pts_ms // 1000
        bucket = buckets.setdefault(second, {"general_flash": 0, "red_flash": 0})
        moving = metric.direction != "flat" and metric.changed_area_fraction >= 0.25
        if moving and metric.luma_delta >= 0.10 and metric.luma_min < 0.80:
            bucket["general_flash"] += 1
        if moving and metric.red_delta >= 0.20:
            bucket["red_flash"] += 1
    if not buckets:
        return []
    return [
        {
            "second": second,
            "general_flash": buckets.get(second, {}).get("general_flash", 0),
            "red_flash": buckets.get(second, {}).get("red_flash", 0),
        }
        for second in range(max(buckets) + 1)
    ]
