from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .detector import detect_general_flashes
from .lineage import regressions
from .models import TransitionMetric, Violation


class ScanRequest(BaseModel):
    parent_metrics: list[TransitionMetric]
    rendition_metrics: list[TransitionMetric]


app = FastAPI(title="Safe Frame API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "healthy",
        "certified_device": False,
        "description": "Open reference-based pre-check implementing published criteria.",
        "integrations": {
            "clickhouse": bool(os.getenv("CLICKHOUSE_HOST")),
            "mcp_clickhouse": bool(os.getenv("MCP_CLICKHOUSE_COMMAND")),
            "google_vertex": bool(os.getenv("GOOGLE_CLOUD_PROJECT")),
        },
    }


@app.post("/v1/scan")
def scan(request: ScanRequest) -> dict[str, object]:
    parent = detect_general_flashes(request.parent_metrics)
    child = detect_general_flashes(request.rendition_metrics)
    introduced = regressions(parent, child)
    return {
        "verdict": "fail" if introduced else "pass",
        "certified": False,
        "gate": {
            "passed": [] if introduced else ["no_child_only_general_flash"],
            "failed": ["no_child_only_general_flash"] if introduced else [],
        },
        "parent_violations": [item.model_dump() for item in parent],
        "rendition_violations": [item.model_dump() for item in child],
        "regressions": [item.model_dump() for item in introduced],
    }


@app.get("/v1/catalogue/regressions")
def catalogue_regressions() -> None:
    if not os.getenv("MCP_CLICKHOUSE_COMMAND"):
        raise HTTPException(503, detail="mcp-clickhouse is not configured; catalogue reads fail closed.")
    raise HTTPException(501, detail="Configure the approved mcp-clickhouse transport before enabling catalogue reads.")
