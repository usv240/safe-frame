from __future__ import annotations

from collections.abc import Sequence

from .models import Regression, Violation


def regressions(parent: Sequence[Violation], child: Sequence[Violation], tolerance_ms: int = 100) -> list[Regression]:
    """Anti-join child violations against parent violations by presentation time."""
    results: list[Regression] = []
    for candidate in child:
        matched = any(
            source.lineage_id == candidate.lineage_id
            and source.rule == candidate.rule
            and abs(source.window_start_ms - candidate.window_start_ms) <= tolerance_ms
            for source in parent
        )
        if not matched:
            results.append(
                Regression(
                    child=candidate,
                    matched_parent=False,
                    attribution=candidate.transform,
                )
            )
    return results
