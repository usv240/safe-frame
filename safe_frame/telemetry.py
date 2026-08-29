"""Structured run logs, shaped for Cloud Logging.

Cloud Run reads JSON on stdout and lifts the well-known fields into the log
entry: `severity` becomes the level, `message` the summary, and everything else
lands in `jsonPayload` where it is queryable. So a single `print` of the right
shape gives structured, filterable telemetry with no client library and no
agent sidecar.

What is worth recording here is narrow and deliberate. An agent that reaches
conclusions from a database is only trustworthy if you can reconstruct, after
the fact, which queries it actually ran and whether the arithmetic or the model
produced the answer. So every agent run logs the tools it called in order and
the decision source, and every fail-closed path logs why it refused rather than
disappearing into a 502.

No payload content is logged: not the metrics submitted to `/v1/scan`, not the
model's prose, not credentials. Operator identifiers are recorded because the
product requires human QC and an audit trail is the point of that requirement.

    gcloud logging read \\
      'jsonPayload.event="agent_run" AND jsonPayload.agent="QcTriageAgent"' \\
      --limit 20 --format json
"""

from __future__ import annotations

import json
import sys
from typing import Any


def log_event(event: str, *, severity: str = "INFO", message: str | None = None, **fields: Any) -> None:
    """Emit one structured entry. Never raises: telemetry must not break a request."""
    try:
        entry: dict[str, Any] = {
            "severity": severity,
            "message": message or event,
            "event": event,
            **fields,
        }
        print(json.dumps(entry, default=str), file=sys.stdout, flush=True)
    except Exception:  # pragma: no cover - logging must never take a request down
        pass
