"""Generate the three sample clips the page offers, from arithmetic.

A judge arriving at "Check your own" usually has no video to hand, which makes
the most convincing part of the product the one nobody tries. These clips remove
that step: one click loads a pair and runs the real analysis.

They are constructed here rather than filmed, so the repository still contains
no third-party footage and `docs/ASSET_RIGHTS.md` stays true. Regenerate with:

    python scripts/make_samples.py

Three files support three scenarios, because the third reuses one of the others:

    master.webm             a calm clip that violates nothing
    rendition-flash.webm    the same content with a luminance flash burst
    rendition-red.webm      a saturated-red alternation at *matched* luminance,
                            which a luminance-only checker passes

    regression      master.webm  + rendition-flash.webm   -> fail
    blind spot      master.webm  + rendition-red.webm     -> fail, red rule only
    inherited       rendition-flash.webm as both sides    -> pass, nothing introduced

**Checking a clip never plays it.** The page decodes these to samples and
measures them, and analysing a clip a visitor supplied never renders it.

The sample files themselves can be played and downloaded, from a collapsed
panel that warns which two contain a flash sequence. They are test patterns, and
a QC engineer evaluating this tool reasonably wants to look at the material, so
the rule is that nothing plays by surprise rather than that nothing plays.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


WIDTH, HEIGHT = 320, 180
FPS = 25
SECONDS = 4
BURST = (1.0, 3.0)  # seconds

# Saturated red and a grey matched to its relative luminance, so an alternation
# between them holds luminance nearly flat while the red difference swings hard.
# OpenCV writes BGR.
RED_BGR = (0, 0, 255)
LUMA_MATCHED_GREY = (124, 124, 124)

OUT = Path(__file__).resolve().parent.parent / "safe_frame" / "web" / "samples"


def _base(index: int) -> np.ndarray:
    """A calm frame with gentle drift, well under every threshold."""
    frame = np.zeros((HEIGHT, WIDTH, 3), np.uint8)
    column = np.linspace(38, 74, WIDTH, dtype=np.float32)
    frame[:, :, 0] = np.clip(column + 3.0 * np.sin(index / 9.0), 0, 255)
    frame[:, :, 1] = np.clip(column + 2.0 * np.sin(index / 11.0), 0, 255)
    frame[:, :, 2] = np.clip(column + 2.0 * np.sin(index / 13.0), 0, 255)
    return frame


def _write(name: str, kind: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"VP80"), FPS, (WIDTH, HEIGHT))
    if not writer.isOpened():
        raise SystemExit("no VP8 encoder available in this OpenCV build")
    first, last = int(BURST[0] * FPS), int(BURST[1] * FPS)
    for index in range(FPS * SECONDS):
        frame = _base(index)
        if kind != "calm" and first <= index < last:
            if kind == "red":
                frame[:, :] = RED_BGR if index % 2 == 0 else LUMA_MATCHED_GREY
            else:
                frame[:, :] = (247, 247, 247) if index % 2 == 0 else (18, 18, 18)
        writer.write(frame)
    writer.release()
    return path


def main() -> None:
    for name, kind in (
        ("master.webm", "calm"),
        ("rendition-flash.webm", "flash"),
        ("rendition-red.webm", "red"),
    ):
        path = _write(name, kind)
        print(f"  {path.name:24s} {path.stat().st_size / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
