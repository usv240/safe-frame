from __future__ import annotations

import asyncio
import os
import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, model_validator

from .clickhouse_ingest import persist_violations
from .clickhouse_mcp import (
    ClickHouseMcp,
    ClickHouseNotConfigured,
    catalogue_regression_evidence,
    regression_count,
)
from .detector import detect_general_flashes
from .lineage import regressions
from .models import TransitionMetric


class ScanRequest(BaseModel):
    parent_metrics: list[TransitionMetric] = Field(min_length=1, max_length=10_000)
    rendition_metrics: list[TransitionMetric] = Field(min_length=1, max_length=10_000)

    @model_validator(mode="after")
    def validate_pair(self) -> "ScanRequest":
        parent_assets = {item.asset_id for item in self.parent_metrics}
        child_assets = {item.asset_id for item in self.rendition_metrics}
        lineages = {item.lineage_id for item in self.parent_metrics + self.rendition_metrics}
        if len(parent_assets) != 1 or len(child_assets) != 1:
            raise ValueError("each side must contain exactly one asset")
        if len(lineages) != 1:
            raise ValueError("parent and rendition must share one lineage_id")
        if parent_assets == child_assets:
            raise ValueError("parent and rendition asset IDs must differ")
        return self


class ExplanationRequest(BaseModel):
    parent_asset: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    child_asset: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    operator_id: str = Field(min_length=2, max_length=120)


app = FastAPI(title="Safe Frame API", version="0.2.0")
_HEALTH_CACHE: dict[str, object] = {"checked": 0.0, "value": None}
WEB_ROOT = os.path.join(os.path.dirname(__file__), "web")


def _configured(*names: str) -> bool:
    return all(bool(os.getenv(name)) for name in names)


def _sample_burst(asset: str, transform: str, count: int) -> list[dict[str, object]]:
    return [
        {
            "asset_id": asset,
            "lineage_id": "judge-tree",
            "parent_id": "approved-master" if asset != "approved-master" else "",
            "transform": transform,
            "pts_ms": index * 100,
            "luma_delta": 0.8,
            "red_delta": 0.0,
            "changed_area_fraction": 1.0,
            "direction": "up" if index % 2 == 0 else "down",
        }
        for index in range(count)
    ]


@app.get("/", include_in_schema=False)
def landing_page() -> FileResponse:
    return FileResponse(os.path.join(WEB_ROOT, "index.html"))


@app.get("/v1/samples")
def samples() -> dict[str, object]:
    return {
        "data": {
            "name": "constructed presentation-time boundary pair",
            "provenance": "self-authored synthetic metrics; no viewer is exposed to flashing imagery",
            "parent_metrics": _sample_burst("approved-master", "master", 6),
            "rendition_metrics": _sample_burst("social-60fps", "frame_rate_conversion", 7),
        }
    }


def _vertex_probe() -> bool:
    from google import genai

    client = genai.Client(
        vertexai=True,
        project=os.environ["GOOGLE_CLOUD_PROJECT"],
        location=os.environ["GOOGLE_CLOUD_LOCATION"],
    )
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents="Reply with exactly OK.",
    )
    return bool(response.text)


async def _integration_health() -> dict[str, bool]:
    now = time.monotonic()
    cached = _HEALTH_CACHE.get("value")
    if cached and now - float(_HEALTH_CACHE["checked"]) < 60:
        return dict(cached)
    clickhouse = False
    google_vertex = False
    if _configured("MCP_CLICKHOUSE_COMMAND", "CLICKHOUSE_HOST", "CLICKHOUSE_PASSWORD"):
        try:
            probe = await ClickHouseMcp().query("SELECT version() AS version")
            clickhouse = not probe["is_error"]
        except Exception:
            clickhouse = False
    if _configured("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION") and os.getenv(
        "GOOGLE_GENAI_USE_VERTEXAI", ""
    ).lower() in {"1", "true", "yes"}:
        try:
            google_vertex = await asyncio.to_thread(_vertex_probe)
        except Exception:
            google_vertex = False
    value = {"clickhouse": clickhouse, "mcp_clickhouse": clickhouse, "google_vertex": google_vertex}
    _HEALTH_CACHE.update(checked=now, value=value)
    return value


@app.get("/health")
async def health() -> dict[str, object]:
    integrations = await _integration_health()
    return {
        "status": "healthy",
        "certified_device": False,
        "description": "Open reference-based pre-check implementing published criteria.",
        "integrations": {**integrations, "agent_runtime_ready": all(integrations.values())},
    }


@app.post("/v1/scan")
async def scan(request: ScanRequest) -> dict[str, object]:
    parent = detect_general_flashes(request.parent_metrics)
    child = detect_general_flashes(request.rendition_metrics)
    local_introduced = regressions(parent, child)
    parent_asset = request.parent_metrics[0].asset_id
    child_asset = request.rendition_metrics[0].asset_id

    sql_proof = None
    introduced_count = len(local_introduced)
    decision_source = "local_reference_precheck"
    if _configured(
        "MCP_CLICKHOUSE_COMMAND", "CLICKHOUSE_HOST", "CLICKHOUSE_PASSWORD",
        "CLICKHOUSE_INGEST_USER", "CLICKHOUSE_INGEST_PASSWORD",
    ):
        await asyncio.to_thread(persist_violations, [*parent, *child])
        try:
            introduced_count, sql_proof = await regression_count(parent_asset, child_asset)
        except Exception as exc:
            raise HTTPException(
                502,
                detail={
                    "code": "clickhouse_mcp_verdict_failed",
                    "message": "The official MCP/SQL verdict failed; Safe Frame refuses to substitute a model or local guess.",
                },
            ) from exc
        decision_source = "clickhouse_sql_via_official_mcp"

    return {
        "verdict": "fail" if introduced_count else "pass",
        "certified": False,
        "decision_source": decision_source,
        "gate": {
            "passed": [] if introduced_count else ["no_child_only_general_flash"],
            "failed": ["no_child_only_general_flash"] if introduced_count else [],
        },
        "parent_violations": [item.model_dump() for item in parent],
        "rendition_violations": [item.model_dump() for item in child],
        "regressions": [item.model_dump() for item in local_introduced],
        "catalogue": {
            "parent_asset": parent_asset,
            "child_asset": child_asset,
            "regression_count": introduced_count,
            "mcp_proof": sql_proof,
        },
    }


@app.get("/v1/catalogue/regressions")
async def catalogue_regressions(parent_asset: str, child_asset: str) -> dict[str, object]:
    try:
        count, proof = await regression_count(parent_asset, child_asset)
    except ClickHouseNotConfigured as exc:
        raise HTTPException(503, detail={"code": "mcp_clickhouse_not_configured", "message": str(exc)}) from exc
    return {
        "data": {
            "verdict": "fail" if count else "pass",
            "regression_count": count,
            "decision_source": "clickhouse_sql_via_official_mcp",
            "mcp": proof,
        }
    }


@app.get("/v1/integrations/clickhouse/evidence")
async def clickhouse_evidence() -> dict[str, object]:
    try:
        client = ClickHouseMcp()
        tools, query = await asyncio.gather(
            client.tools(),
            client.query(
                "SELECT count() AS violations, uniqExact(lineage_id) AS lineages "
                "FROM safe_frame.violations"
            ),
        )
    except ClickHouseNotConfigured as exc:
        raise HTTPException(503, detail={"code": "mcp_clickhouse_not_configured", "message": str(exc)}) from exc
    return {
        "data": {
            "transport": "official_mcp_clickhouse_stdio",
            "read_only": True,
            "required_tools_advertised": {name: name in tools for name in ("run_query", "list_databases", "list_tables")},
            "query": query,
        }
    }


@app.post("/v1/explain")
async def explain(request: ExplanationRequest) -> dict[str, object]:
    from .adk_app import explain_regression

    try:
        result = await explain_regression(request.parent_asset, request.child_asset, request.operator_id)
    except Exception as exc:
        raise HTTPException(
            502,
            detail={"code": "agent_explanation_failed", "message": "ADK could not complete the MCP-grounded explanation."},
        ) from exc
    return {"data": result}
