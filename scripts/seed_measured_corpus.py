"""Seed a cohort of the catalogue whose rows are MEASURED from pixels.

Every other row in `safe_frame.transitions` is an authored number: SQL decided
what `luma_delta` should be and wrote it. That exercises the criteria, the
lineage isolation and the controls at scale, but it never runs the measurement
stage, and `docs/CRITERIA.md` said so as a standing gap.

This closes it. Each asset here is built as an actual sequence of RGB frames,
pushed through `safe_frame.ingest.frames_to_transitions` — the same function the
product would use on decoded video — and the resulting rows are inserted
alongside the authored ones. Nothing about the numbers is chosen; they fall out
of `relative_luminance` and `red_flash_mask` over real pixel arrays.

The frames are constructed, not filmed, and no sequence is ever rendered or
displayed. They exist as numpy arrays for the length of one measurement.

Planting stays recoverable without looking at any measurement, so the evaluation
in `/v1/evaluation` still scores this cohort the same way it scores the authored
one. The authored cohort plants with `sipHash64`; reproducing that hash in Python
is awkward, so this cohort plants on plain arithmetic over the title index, which
`sql/008_ground_truth.sql` recomputes exactly.

    inherited      idx % 11 == 3    burst in the master too, so no rendition
                                    introduced anything and none may be returned
    general flash  idx % 4 == 0     in 60fps_interp and adbreak_insert only
    red flash      idx % 5 == 1     in social_crop_v and subtitle_burnin only
    bright decoy   idx % 6 == 2     in hdr10_passthrough: a full-amplitude
                                    alternation between two states that are both
                                    above the published 0.80 darker-image
                                    ceiling, which must NOT be returned

Usage (needs the ingest credential and clickhouse-connect):

    CLICKHOUSE_HOST=... CLICKHOUSE_INGEST_USER=... CLICKHOUSE_INGEST_PASSWORD=... \\
        python scripts/seed_measured_corpus.py --titles 24
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from safe_frame.ingest import frames_to_transitions  # noqa: E402
from safe_frame.metrics import relative_luminance  # noqa: E402

SIZE = 32
FRAME_RATE = 25.0
SECONDS = 120
FRAMES = SECONDS * int(FRAME_RATE) + 1

TRANSFORMS = [
    "master", "sdr_tonemap", "1080p_downscale", "60fps_interp",
    "social_crop_v", "adbreak_insert", "subtitle_burnin", "hdr10_passthrough",
]

BURST_CAPABLE = {"60fps_interp", "adbreak_insert"}
RED_CAPABLE = {"social_crop_v", "subtitle_burnin"}
BRIGHT_CAPABLE = {"hdr10_passthrough"}


def solid(rgb: tuple[float, float, float]) -> np.ndarray:
    return np.tile(np.array(rgb, dtype=float), (SIZE, SIZE, 1))


def _matched_luminance_teal() -> np.ndarray:
    """A blue-green whose relative luminance equals saturated red's.

    Solved against the shipped implementation rather than hard-coded, because
    the answer depends on sRGB linearisation. This is what makes the red cohort
    invisible to the luminance rule: the two states differ in saturated red by
    the full range and in luminance by almost nothing.
    """
    target = float(relative_luminance(solid((1.0, 0.0, 0.0)))[0, 0])
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if float(relative_luminance(solid((0.0, mid, mid)))[0, 0]) < target:
            lo = mid
        else:
            hi = mid
    return solid((0.0, (lo + hi) / 2, (lo + hi) / 2))


BASE_A = solid((0.10, 0.10, 0.10))
BASE_B = solid((0.55, 0.55, 0.55))
BURST_DARK = solid((0.02, 0.02, 0.02))
BURST_LIGHT = solid((0.95, 0.95, 0.95))
BRIGHT_LOW = solid((0.93, 0.93, 0.93))
BRIGHT_HIGH = solid((1.00, 1.00, 1.00))
RED = solid((1.0, 0.0, 0.0))
TEAL = _matched_luminance_teal()


def plan(idx: int, transform: str) -> dict[str, object]:
    """What is planted in this asset, decided before any pixel exists.

    An inherited title carries its burst in EVERY transform including the
    master, which is what makes those renditions decoys: they really do flash,
    and they introduced nothing, so the anti-join must exclude them. That has to
    be independent of whether a regression was also planted, or a small cohort
    ends up with no inherited decoys at all.

    Burst seconds never overlap between rules (bright 10-24, general 30-69,
    red 95-114), so one asset can carry more than one without them interfering.
    """
    inherited_general = idx % 11 == 3
    inherited_red = idx % 13 == 5

    general = inherited_general or (transform in BURST_CAPABLE and idx % 4 == 0)
    red = inherited_red or (transform in RED_CAPABLE and idx % 5 == 1)
    bright = transform in BRIGHT_CAPABLE and idx % 6 == 2

    return {
        "inherited_general": inherited_general,
        "inherited_red": inherited_red,
        "general_second": 30 + (idx % 40) if general else None,
        "red_second": 95 + (idx % 20) if red else None,
        "bright_second": 10 + (idx % 15) if bright else None,
    }


def frames_for(idx: int, transform: str):
    """Yield the frame sequence for one asset.

    Baseline changes only every sixth frame, so roughly 4.2 transitions a second
    qualify — deliberately just under the criterion, so ordinary content never
    trips the rule and the bursts are the only thing that can.
    """
    p = plan(idx, transform)
    g, r, b = p["general_second"], p["red_second"], p["bright_second"]
    for i in range(FRAMES):
        second = i // int(FRAME_RATE)
        if g is not None and second == g:
            yield BURST_DARK if i % 2 else BURST_LIGHT
        elif r is not None and second == r:
            yield RED if i % 2 else TEAL
        elif b is not None and second == b:
            yield BRIGHT_LOW if i % 2 else BRIGHT_HIGH
        else:
            yield BASE_A if (i // 6) % 2 else BASE_B


COLUMNS = [
    "asset_id", "lineage_id", "parent_id", "transform", "pts_ms",
    "luma_delta", "luma_min", "red_delta", "changed_area_fraction", "direction",
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--titles", type=int, default=24)
    ap.add_argument("--dry-run", action="store_true", help="measure but do not insert")
    args = ap.parse_args()

    client = None
    if not args.dry_run:
        import clickhouse_connect

        client = clickhouse_connect.get_client(
            host=os.environ["CLICKHOUSE_HOST"],
            port=int(os.getenv("CLICKHOUSE_PORT", "443")),
            username=os.environ["CLICKHOUSE_INGEST_USER"],
            password=os.environ["CLICKHOUSE_INGEST_PASSWORD"],
            database=os.getenv("CLICKHOUSE_DATABASE", "safe_frame"),
            secure=os.getenv("CLICKHOUSE_SECURE", "true").lower() == "true",
        )

    started = time.perf_counter()
    total = 0
    planted = {"general": 0, "red": 0, "bright_decoy": 0, "inherited_titles": 0}

    for idx in range(args.titles):
        lineage = f"measured_{idx:04d}"
        if idx % 11 == 3 or idx % 13 == 5:
            planted["inherited_titles"] += 1
        for transform in TRANSFORMS:
            asset = f"{lineage}__{transform}"
            parent = "" if transform == "master" else f"{lineage}__master"
            rows = [
                [getattr(m, c) for c in COLUMNS]
                for m in frames_to_transitions(
                    frames_for(idx, transform),
                    asset_id=asset, lineage_id=lineage, parent_id=parent,
                    transform=transform, frame_rate=FRAME_RATE,
                )
            ]
            if client is not None:
                client.insert("transitions", rows, column_names=COLUMNS)
            total += len(rows)

            p = plan(idx, transform)
            if transform != "master":
                if (p["general_second"] is not None and transform in BURST_CAPABLE
                        and not p["inherited_general"]):
                    planted["general"] += 1
                if (p["red_second"] is not None and transform in RED_CAPABLE
                        and not p["inherited_red"]):
                    planted["red"] += 1
                if p["bright_second"] is not None:
                    planted["bright_decoy"] += 1
        print(f"  {lineage}: {total:,} rows measured", flush=True)

    elapsed = time.perf_counter() - started
    print(f"\n{total:,} transitions measured from pixels in {elapsed:.0f}s "
          f"({'inserted' if client else 'dry run, not inserted'})")
    print(f"planted: {planted['general']} general, {planted['red']} red, "
          f"{planted['bright_decoy']} bright decoys, "
          f"{planted['inherited_titles']} inherited titles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
