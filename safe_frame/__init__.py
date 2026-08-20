"""Reference-based photosensitivity regression pre-check."""

from .detector import detect_general_flashes
from .lineage import regressions

__all__ = ["detect_general_flashes", "regressions"]
