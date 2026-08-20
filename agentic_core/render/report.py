"""Safe report views over structured results; never a second source of truth."""

from __future__ import annotations

import html
import json
from typing import Any, Mapping


def render_json(report: Mapping[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True, default=str)


def render_html(report: Mapping[str, Any]) -> str:
    verdict = html.escape(str(report.get("verdict", "unknown")))
    reason = html.escape(str(report.get("reason", "No reason was supplied.")))
    thresholds = report.get("thresholds", {})
    if not isinstance(thresholds, Mapping):
        raise TypeError("report thresholds must be a mapping")
    rows = "".join(
        "<tr><th scope='row'>{}</th><td>{}</td></tr>".format(
            html.escape(str(name)), "PASS" if passed else "FAIL"
        )
        for name, passed in thresholds.items()
    )
    return (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<title>Evidence report</title><body><main>"
        f"<h1>Verdict: {verdict}</h1><p>{reason}</p>"
        f"<table><caption>Deterministic gate</caption>{rows}</table>"
        "</main></body></html>"
    )

