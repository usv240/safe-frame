"""Pixel measurements, implementing the published definitions rather than
approximations of them.

Two of these were wrong before an audit against the primary sources, and both
mattered:

* `relative_luminance` applied the BT.709 coefficients directly to sRGB samples.
  WCAG's normative definition requires the channels to be **linearised first**
  — sRGB is gamma-encoded, so weighting the encoded values overstates the
  luminance of dark pixels and understates bright ones. Every threshold
  downstream is expressed against that definition, so the error propagated into
  the general-flash rule.
* `saturated_red` returned `R - max(G, B)`, which is a plausible-looking proxy
  and not the published test. WCAG defines saturated red precisely, and the
  definition is now implemented as written.

See `docs/CRITERIA.md` for the quoted definitions and the deviations that
remain.
"""

from __future__ import annotations

import numpy as np


def _linearise(channel: np.ndarray) -> np.ndarray:
    """Undo sRGB gamma encoding, per the WCAG relative-luminance definition.

    `if c <= 0.04045: c / 12.92 else ((c + 0.055) / 1.055) ** 2.4`

    The threshold was 0.03928 in the pre-2021 text; W3C corrected it to 0.04045
    and this follows the current definition.
    """
    return np.where(channel <= 0.04045, channel / 12.92, ((channel + 0.055) / 1.055) ** 2.4)


def _check(rgb: np.ndarray) -> None:
    if rgb.ndim != 3 or rgb.shape[-1] != 3:
        raise ValueError("expected HxWx3 RGB frame")
    if rgb.min() < 0 or rgb.max() > 1:
        raise ValueError("RGB samples must be normalized to 0..1")


def relative_luminance(rgb: np.ndarray) -> np.ndarray:
    """WCAG relative luminance: 0 for darkest black, 1 for lightest white.

    `L = 0.2126 R + 0.7152 G + 0.0722 B` over **linearised** sRGB channels.
    """
    _check(rgb)
    linear = _linearise(rgb)
    return 0.2126 * linear[..., 0] + 0.7152 * linear[..., 1] + 0.0722 * linear[..., 2]


def saturated_red(frame: np.ndarray) -> np.ndarray:
    """Per-pixel mask of pixels that are a saturated red, as WCAG defines it.

    > for either or both states involved in each transition,
    > `R / (R + G + B) >= 0.8`

    Uses the sRGB values as given, not linearised: the published test is stated
    over R, G and B directly.
    """
    _check(frame)
    total = frame.sum(axis=-1)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(total > 0, frame[..., 0] / np.where(total > 0, total, 1), 0.0)
    return ratio >= 0.8


def red_difference(frame: np.ndarray) -> np.ndarray:
    """The `(R - G - B) x 320` quantity WCAG's red-flash test is stated over.

    A transition counts toward the red rule when a pixel is a saturated red in
    at least one of the two states **and** this value changes by more than 20.
    """
    _check(frame)
    return (frame[..., 0] - frame[..., 1] - frame[..., 2]) * 320.0


def red_flash_mask(previous: np.ndarray, current: np.ndarray) -> np.ndarray:
    """Pixels that satisfy the published red-flash transition test.

    > any pair of opposing transitions involving a saturated red, where for
    > either or both states `R/(R+G+B) >= 0.8` and the change in the value of
    > `(R-G-B) x 320` is greater than 20.
    """
    involves_saturated_red = saturated_red(previous) | saturated_red(current)
    swing = np.abs(red_difference(current) - red_difference(previous))
    return involves_saturated_red & (swing > 20.0)


def changed_area_direct(previous: np.ndarray, current: np.ndarray, threshold: float = 0.1) -> float:
    """Measure affected screen area directly, before any lossy tile aggregation.

    This is a fraction of the **frame**, which is a documented simplification of
    the published area condition — see `docs/CRITERIA.md`.
    """
    delta = np.abs(relative_luminance(current) - relative_luminance(previous))
    return float(np.mean(delta >= threshold))


def tile_luminance(frame: np.ndarray, rows: int = 8, columns: int = 8) -> np.ndarray:
    """Diagnostic tile averages. Never use these to estimate changed screen area."""
    luma = relative_luminance(frame)
    height, width = luma.shape
    if height % rows or width % columns:
        raise ValueError("frame dimensions must divide evenly into the tile grid")
    return luma.reshape(rows, height // rows, columns, width // columns).mean(axis=(1, 3))


def changed_area_from_tiles(previous: np.ndarray, current: np.ndarray, threshold: float = 0.1) -> float:
    delta = np.abs(tile_luminance(current) - tile_luminance(previous))
    return float(np.mean(delta >= threshold))
