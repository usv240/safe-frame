from __future__ import annotations

import numpy as np


def cross_dissolve(previous: np.ndarray, current: np.ndarray, steps: int = 4) -> list[np.ndarray]:
    if steps < 2:
        raise ValueError("steps must be at least two")
    return [previous * (1 - alpha) + current * alpha for alpha in np.linspace(0, 1, steps + 2)[1:-1]]


def luminance_clamp(previous: np.ndarray, current: np.ndarray, maximum_delta: float = 0.09) -> np.ndarray:
    return np.clip(current, previous - maximum_delta, previous + maximum_delta)
