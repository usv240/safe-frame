from __future__ import annotations

import os
from collections.abc import Sequence

from .models import Violation


def _client():
    import clickhouse_connect

    return clickhouse_connect.get_client(
        host=os.environ["CLICKHOUSE_HOST"],
        port=int(os.getenv("CLICKHOUSE_PORT", "443")),
        username=os.environ["CLICKHOUSE_INGEST_USER"],
        password=os.environ["CLICKHOUSE_INGEST_PASSWORD"],
        database=os.getenv("CLICKHOUSE_DATABASE", "safe_frame"),
        secure=os.getenv("CLICKHOUSE_SECURE", "true").lower() == "true",
        verify=os.getenv("CLICKHOUSE_VERIFY", "true").lower() == "true",
    )


def persist_violations(violations: Sequence[Violation]) -> int:
    if not violations:
        return 0
    columns = [
        "asset_id", "lineage_id", "parent_id", "transform", "rule",
        "window_start_ms", "window_end_ms", "transitions", "peak_changed_area_fraction",
    ]
    rows = [[getattr(item, column) for column in columns] for item in violations]
    _client().insert("violations", rows, column_names=columns)
    return len(rows)
