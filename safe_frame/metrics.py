from __future__ import annotations

import numpy as np


def relative_luminance(rgb: np.ndarray) -> np.ndarray:
    """Return BT.709 relative luminance for normalized RGB pixels."""
    if rgb.ndim != 3 or rgb.shape[-1] != 3:
        raise ValueError("expected HxWx3 RGB frame")
    if rgb.min() < 0 or rgb.max() > 1:
        raise ValueError("RGB samples must be normalized to 0..1")
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def changed_area_direct(previous: np.ndarray, current: np.ndarray, threshold: float = 0.1) -> float:
    """Measure affected screen area before any lossy tile aggregation."""
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


def saturated_red(frame: np.ndarray) -> np.ndarray:
    red = frame[..., 0]
    other = np.maximum(frame[..., 1], frame[..., 2])
    return np.clip(red - other, 0, 1)
