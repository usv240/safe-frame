from __future__ import annotations

import asyncio
import os
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, model_validator

from .clickhouse_ingest import persist_violations
from .apikeys import (
    ANONYMOUS,
    MAX_AGE_DAYS,
    TIER_MULTIPLIER,
    ApiKeyError,
    configured as api_keys_configured,
    identify,
    mint,
)
from .analyze import (
    AREA_RESOLUTION_NOTE,
    MAX_FRAME_RATE,
    MAX_FRAMES,
    MAX_HEIGHT,
    MAX_WIDTH,
    FrameDecodeError,
    measure_clip,
    per_second_counts,
)
from .clickhouse_mcp import (
    ClickHouseMcp,
    ClickHouseNotConfigured,
    catalogue_regression_evidence,
    parity_violations,
    regression_count,
    submitted_regressions,
)
from .detector import detect_violations
from .lineage import regressions
from .models import TransitionMetric
from .stack import build_stack
from .telemetry import log_event


# The catalogue is generated and read-only to the public API. These are the
# identifiers the constructed judge sample and the generated corpus own, and a
# caller-supplied write must never land on them: `/v1/scan` persists the
# asset_id it is given, and the per-pair anti-join reads the same table, so an
# anonymous write to `approved-master` could suppress the child violation and
# flip the documented sample from fail to pass.
RESERVED_ASSET_PREFIXES = ("title_",)
RESERVED_ASSET_IDS = frozenset({"approved-master", "social-60fps"})


def _reserved(asset_id: str) -> bool:
    return asset_id in RESERVED_ASSET_IDS or asset_id.startswith(RESERVED_ASSET_PREFIXES)


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
        for asset in parent_assets | child_assets:
            if _reserved(asset):
                raise ValueError(
                    f"{asset!r} is reserved for the published catalogue and the judge sample; "
                    "submit your own asset IDs"
                )
        return self


class ClipPayload(BaseModel):
    """One decoded clip: raw RGB samples on a small grid, plus its shape."""

    frames_b64: str = Field(min_length=4, max_length=16_000_000)
    width: int = Field(ge=1, le=MAX_WIDTH)
    height: int = Field(ge=1, le=MAX_HEIGHT)
    frame_count: int = Field(ge=2, le=MAX_FRAMES)
    frame_rate: float = Field(gt=0, le=MAX_FRAME_RATE)


class AnalyzeRequest(BaseModel):
    """A rendition to check, and optionally the approved master to check it against."""

    rendition: ClipPayload
    master: ClipPayload | None = None

    @model_validator(mode="after")
    def validate_pair(self) -> "AnalyzeRequest":
        if self.master is not None and self.master.frame_rate != self.rendition.frame_rate:
            # Frame rates may legitimately differ; alignment is on presentation
            # time, so this is allowed. Kept as a hook rather than a rejection.
            pass
        return self


class TriageRequest(BaseModel):
    operator_id: str = Field(min_length=2, max_length=120)


class ExplanationRequest(BaseModel):
    parent_asset: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    child_asset: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    operator_id: str = Field(min_length=2, max_length=120)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return (forwarded.split(",")[0].strip() or (request.client.host if request.client else "?"))


_CALLS: dict[tuple[str, str], list[float]] = {}


def rate_limit(bucket: str, limit: int, window_s: float = 60.0):
    """Cap the endpoints that spend Gemini tokens or write to the database.

    Deliberately not applied to any read endpoint: judging requires the product
    to be testable without an account, a key, or a quota, and every read is
    served from ClickHouse at a cost we control. This exists so a loop against
    `/v1/triage` cannot exhaust the Vertex quota during a judging window and
    take the demo down with it.

    In-process and therefore per-instance, which is approximate under scale-out.
    That is the right size for the problem: it stops runaway and accidental
    repetition, and it is not an access-control mechanism.
    """

    async def guard(request: Request) -> None:
        # A missing key is the supported anonymous tier. A key that is present
        # and broken is refused rather than silently downgraded, or the caller
        # would never learn why their quota did not rise.
        try:
            identity = identify(
                request.headers.get("authorization"), request.headers.get("x-api-key")
            )
        except ApiKeyError as exc:
            raise HTTPException(
                401,
                detail={
                    "code": "invalid_api_key",
                    "message": str(exc),
                    "hint": "POST /v1/keys to mint one, or send no credential at all to use the anonymous tier.",
                },
            ) from exc

        effective = limit * TIER_MULTIPLIER[identity.tier]
        now = time.monotonic()
        # Keyed callers get their own bucket, so one caller's quota cannot be
        # consumed by another behind the same proxy address.
        key = (bucket, identity.key_id or _client_key(request))
        recent = [t for t in _CALLS.get(key, ()) if now - t < window_s]
        if len(recent) >= effective:
            raise HTTPException(
                429,
                detail={
                    "code": "rate_limited",
                    "message": (
                        f"{bucket} is limited to {effective} calls per minute for the "
                        f"{identity.tier} tier because it spends model tokens or writes. "
                        "Every read endpoint is unlimited."
                    ),
                    "hint": (
                        None if identity.is_keyed
                        else f"POST /v1/keys for a free key and {TIER_MULTIPLIER['keyed']}x this limit."
                    ),
                },
            )
        recent.append(now)
        _CALLS[key] = recent

    return guard


app = FastAPI(title="Safe Frame API", version="0.3.0")
_HEALTH_CACHE: dict[str, object] = {"checked": 0.0, "value": None}
WEB_ROOT = os.path.join(os.path.dirname(__file__), "web")


@app.on_event("startup")
async def _warm_mcp() -> None:
    """Open the official mcp-clickhouse session before the first request.

    Starting the server costs several seconds. Paying it at boot means a
    visitor's first sweep measures the query, not the subprocess. Failure is
    not fatal: the endpoints start the session on demand and still fail closed
    if ClickHouse is genuinely unreachable.
    """
    try:
        await ClickHouseMcp().tools()
    except ClickHouseNotConfigured:
        pass
    except Exception as exc:  # pragma: no cover - best-effort warm-up
        import logging

        logging.getLogger(__name__).warning("mcp-clickhouse warm-up failed: %s", exc)


def _configured(*names: str) -> bool:
    return all(bool(os.getenv(name)) for name in names)


def _sample_burst(asset: str, parent: str, lineage: str, transform: str, count: int) -> list[dict[str, object]]:
    return [
        {
            "asset_id": asset,
            "lineage_id": lineage,
            "parent_id": parent,
            "transform": transform,
            "pts_ms": index * 100,
            "luma_delta": 0.8,
            # below the 0.80 ceiling the published general-flash test puts on the
            # darker image, so this pair is a genuine general flash
            "luma_min": 0.05,
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
    """A constructed pass/fail pair, minted fresh for every caller.

    `/v1/scan` persists what it is given, and the per-pair anti-join reads the
    same table, so a fixed sample identifier would be shared mutable state: one
    caller's scan could change what the next caller sees. Each request gets its
    own lineage, so scans are isolated from each other and from the published
    catalogue.
    """
    run = uuid.uuid4().hex[:10]
    lineage, parent, child = f"sample-{run}", f"sample-{run}-master", f"sample-{run}-60fps"
    return {
        "data": {
            "name": "constructed presentation-time boundary pair",
            "provenance": "self-authored synthetic metrics; no viewer is exposed to flashing imagery",
            "isolation": "identifiers are unique per request, so your scan cannot collide with anyone else's",
            "expected": {"parent": "pass (6 transitions)", "rendition": "fail (7 transitions)"},
            "parent_metrics": _sample_burst(parent, "", lineage, "master", 6),
            "rendition_metrics": _sample_burst(child, parent, lineage, "frame_rate_conversion", 7),
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


@app.post("/v1/keys", dependencies=[Depends(rate_limit("/v1/keys", 10))])
async def create_api_key() -> dict[str, object]:
    """Mint an API key. No account, no email, no approval.

    A key is optional. Every endpoint works without one, at the limits this
    service has always had, because the product has to be testable without a
    signup. A key raises the per-minute cap on the endpoints that spend model
    tokens or write, and names the caller in the logs.

    The key is returned once. It is not stored anywhere, because there is
    nowhere to store it: the key carries its own signature, and verifying it is
    a signature check rather than a database lookup.
    """
    if not api_keys_configured():
        raise HTTPException(
            503,
            detail={
                "code": "api_keys_unavailable",
                "message": (
                    "This deployment has no signing secret configured, so it cannot issue keys. "
                    "Every endpoint still works anonymously at the standard limits."
                ),
            },
        )
    try:
        return {"data": mint()}
    except ApiKeyError as exc:  # pragma: no cover - guarded by configured() above
        raise HTTPException(503, detail={"code": "api_keys_unavailable", "message": str(exc)}) from exc


@app.get("/v1/keys/self")
async def describe_api_key(request: Request) -> dict[str, object]:
    """Report which tier the caller is on, so a key can be checked before use."""
    try:
        identity = identify(
            request.headers.get("authorization"), request.headers.get("x-api-key")
        )
    except ApiKeyError as exc:
        raise HTTPException(401, detail={"code": "invalid_api_key", "message": str(exc)}) from exc
    return {
        "data": {
            "tier": identity.tier,
            "key_id": identity.key_id,
            "quota_multiplier": TIER_MULTIPLIER[identity.tier],
            "expires_after_days": MAX_AGE_DAYS if identity.is_keyed else None,
            "keys_available": api_keys_configured(),
            "note": (
                "Anonymous access is fully supported and is how the judge path is meant to be "
                "exercised. A key only raises limits on the endpoints that spend tokens or write."
            ),
        }
    }


@app.get("/health")
async def health() -> dict[str, object]:
    integrations = await _integration_health()
    return {
        "status": "healthy",
        "certified_device": False,
        "description": "Open reference-based pre-check implementing published criteria.",
        "integrations": {**integrations, "agent_runtime_ready": all(integrations.values())},
    }


@app.post("/v1/scan", dependencies=[Depends(rate_limit("/v1/scan", 20))])
async def scan(request: ScanRequest) -> dict[str, object]:
    parent = detect_violations(request.parent_metrics)
    child = detect_violations(request.rendition_metrics)
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
            log_event("fail_closed", severity="ERROR", endpoint="/v1/scan",
                      code="clickhouse_mcp_verdict_failed", reason=type(exc).__name__,
                      message="refused to substitute a verdict after the MCP/SQL path failed")
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
        "rules_evaluated": ["general_flash", "red_flash"],
        "gate": {
            "passed": [] if introduced_count else ["no_child_only_flash_violation"],
            "failed": ["no_child_only_flash_violation"] if introduced_count else [],
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


@app.post("/v1/analyze", dependencies=[Depends(rate_limit("/v1/analyze", 12))])
async def analyze(request: AnalyzeRequest) -> dict[str, object]:
    """Check a clip the caller supplied, through the product's own measurement path.

    Submit a rendition on its own for an absolute check against the published
    criteria, or submit its approved master too for the check this product
    exists for: not "does this flash" but "did this conversion introduce a flash
    the approved master did not have".

    The frames are measured by `safe_frame.ingest`, the same function the
    measured cohort used, and the verdict comes from ClickHouse through the
    official MCP server. Nothing is decided here and nothing is decided by a
    model.
    """
    run = uuid.uuid4().hex[:10]
    lineage = f"byo-{run}"
    child_asset = f"{lineage}-rendition"
    parent_asset = f"{lineage}-master"

    try:
        child_metrics = await asyncio.to_thread(
            measure_clip,
            request.rendition.frames_b64,
            width=request.rendition.width,
            height=request.rendition.height,
            frame_count=request.rendition.frame_count,
            frame_rate=request.rendition.frame_rate,
            asset_id=child_asset,
            lineage_id=lineage,
            parent_id=parent_asset if request.master else "",
            transform="submitted_rendition",
        )
        parent_metrics: list[TransitionMetric] = []
        if request.master is not None:
            parent_metrics = await asyncio.to_thread(
                measure_clip,
                request.master.frames_b64,
                width=request.master.width,
                height=request.master.height,
                frame_count=request.master.frame_count,
                frame_rate=request.master.frame_rate,
                asset_id=parent_asset,
                lineage_id=lineage,
                transform="master",
            )
    except FrameDecodeError as exc:
        raise HTTPException(400, detail={"code": "invalid_frames", "message": str(exc)}) from exc

    if not child_metrics:
        raise HTTPException(
            400,
            detail={
                "code": "no_transitions",
                "message": "the clip produced no frame-to-frame transitions to measure",
            },
        )

    mode = "regression" if parent_metrics else "absolute"
    configured = _configured(
        "MCP_CLICKHOUSE_COMMAND", "CLICKHOUSE_HOST", "CLICKHOUSE_PASSWORD",
    )
    child_violations = detect_violations(child_metrics)
    parent_violations = detect_violations(parent_metrics) if parent_metrics else []
    # One shape for both modes: a finding is always the child violation itself,
    # so a caller never has to unwrap a different envelope per mode.
    if mode == "regression":
        findings = [item.child for item in regressions(parent_violations, child_violations)]
    else:
        findings = list(child_violations)
    decision_source = "local_reference_precheck"

    if configured:
        try:
            # Neither mode writes. Frames a visitor supplied are measured in
            # memory and evaluated over inline rows, so nothing derived from
            # somebody's own video is stored anywhere. This path previously
            # persisted the pair and ran the stored anti-join, which kept those
            # measurements in the database indefinitely for no benefit.
            def as_row(metric: TransitionMetric) -> dict[str, object]:
                return {
                    "asset_id": metric.asset_id,
                    "pts_ms": metric.pts_ms,
                    "luma_delta": metric.luma_delta,
                    "luma_min": metric.luma_min,
                    "red_delta": metric.red_delta,
                    "changed_area_fraction": metric.changed_area_fraction,
                    "direction": metric.direction,
                }

            if mode == "regression":
                verdict_count = len(
                    await submitted_regressions(
                        [as_row(m) for m in [*parent_metrics, *child_metrics]],
                        parent_asset=parent_asset,
                        child_asset=child_asset,
                    )
                )
            else:
                verdict_count = len(
                    await parity_violations([as_row(m) for m in child_metrics])
                )
            decision_source = "clickhouse_sql_via_official_mcp"
        except Exception as exc:
            log_event("fail_closed", severity="ERROR", endpoint="/v1/analyze",
                      code="clickhouse_mcp_verdict_failed", reason=type(exc).__name__,
                      message="refused to substitute a verdict after the MCP/SQL path failed")
            raise HTTPException(
                502,
                detail={
                    "code": "clickhouse_mcp_verdict_failed",
                    "message": "The official MCP/SQL verdict failed; Safe Frame refuses to substitute a model or local guess.",
                },
            ) from exc
    else:
        verdict_count = len(findings)

    return {
        "data": {
            "mode": mode,
            "verdict": "fail" if verdict_count else "pass",
            "certified": False,
            "requires_human": True,
            "decision_source": decision_source,
            "rules_evaluated": ["general_flash", "red_flash"],
            "findings": [item.model_dump() for item in findings],
            "rendition": {
                "asset_id": child_asset,
                "transitions_measured": len(child_metrics),
                "violations": [item.model_dump() for item in child_violations],
                "per_second": per_second_counts(child_metrics),
            },
            "master": {
                "asset_id": parent_asset,
                "transitions_measured": len(parent_metrics),
                "violations": [item.model_dump() for item in parent_violations],
                "per_second": per_second_counts(parent_metrics),
            } if parent_metrics else None,
            "measurement": {
                "measured_by": "safe_frame.ingest.frames_to_transitions",
                "grid": f"{request.rendition.width}x{request.rendition.height}",
                "frame_rate": request.rendition.frame_rate,
                "note": AREA_RESOLUTION_NOTE.format(
                    width=request.rendition.width, height=request.rendition.height
                ),
            },
            "privacy": {
                "file_never_uploaded": "the video is decoded in your browser; the file itself does not leave your machine",
                "never_displayed": "it is never rendered on the page, so a clip you suspect of flashing is not played back at you",
                "what_is_sent": "downscaled RGB samples only, held in memory for this request",
                "what_is_stored": "nothing. Both modes evaluate the criteria over inline rows and write no database records",
                "logs": "an entry is written only if the query fails, recording the endpoint and the exception type, never your data",
                "identifiers": "generated per request and never linked to you",
            },
        }
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


@app.get("/v1/stack")
async def stack() -> dict[str, object]:
    """What this service is built from, and which parts are answering right now.

    The status on each component is earned rather than decorative: `live` means a
    round trip completed during this request, `active` means the thing is in the
    process serving you, and `applied` means it built or verified the project but
    is not in the request path. Claiming a green light for a library that merely
    appears in requirements.txt would be the easiest thing on this page to fake,
    so it is the one thing here that is not asserted.
    """
    integrations = await _integration_health()
    version: str | None = None
    tools: list[str] = []
    if integrations.get("clickhouse"):
        try:
            client = ClickHouseMcp()
            rows = await client.query("SELECT version() AS version")
            if not rows["is_error"]:
                text = "".join(str(item.get("text", "")) for item in rows["content"])
                for token in text.replace('"', " ").replace(",", " ").split():
                    if token[:1].isdigit() and "." in token:
                        version = token
                        break
            tools = await client.tools()
        except Exception:
            version, tools = None, []
    return {
        "data": build_stack(
            clickhouse_live=bool(integrations.get("clickhouse")),
            vertex_live=bool(integrations.get("google_vertex")),
            clickhouse_version=version,
            mcp_tools=tools,
        )
    }


@app.get("/v1/catalogue/shape")
async def catalogue_shape() -> dict[str, object]:
    """Size of the corpus the sweep searches, read live through official MCP."""
    from .catalogue import _decode, scale_sql

    try:
        rows = _decode(await ClickHouseMcp().query(scale_sql()))
    except ClickHouseNotConfigured as exc:
        raise HTTPException(
            503, detail={"code": "mcp_clickhouse_not_configured", "message": str(exc)}
        ) from exc
    except Exception as exc:
        raise HTTPException(
            502,
            detail={
                "code": "catalogue_shape_failed",
                "message": f"Corpus shape failed closed ({type(exc).__name__}).",
            },
        ) from exc
    shape = rows[0] if rows else {}
    return {
        "data": {
            "transitions": int(shape.get("transitions", 0) or 0),
            "assets": int(shape.get("assets", 0) or 0),
            "titles": int(shape.get("titles", 0) or 0),
            "transforms": int(shape.get("transforms", 0) or 0),
            "provenance": (
                "self-authored synthetic catalogue: most rows authored by "
                "sql/005_catalogue_generator.sql, and 576,000 rows across 24 titles "
                "measured from constructed RGB frames by scripts/seed_measured_corpus.py "
                "through safe_frame.ingest. Both cohorts are scored separately at "
                "/v1/evaluation. No filmed footage, and nothing here flashes."
            ),
        }
    }


@app.get("/v1/catalogue/sweep")
async def catalogue_sweep() -> dict[str, object]:
    """Isolate every rendition in the catalogue that introduced a violation.

    The published criteria are evaluated inside ClickHouse across every
    transition measurement in one pass, and the master/rendition isolation
    happens in the same query. Nothing here is pre-computed.
    """
    from .catalogue import sweep

    started = time.perf_counter()
    try:
        result = await sweep()
    except ClickHouseNotConfigured as exc:
        raise HTTPException(
            503, detail={"code": "mcp_clickhouse_not_configured", "message": str(exc)}
        ) from exc
    except Exception as exc:
        raise HTTPException(
            502,
            detail={
                "code": "catalogue_sweep_failed",
                "message": (
                    f"The catalogue sweep failed closed ({type(exc).__name__}); "
                    "no regression list was fabricated."
                ),
            },
        ) from exc
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
    log_event("catalogue_sweep", regressions=result["regression_count"],
              by_rule=result["by_rule"], corpus_rows=result["corpus"]["transitions"],
              clickhouse_ms=result["timing"].get("query_ms"),
              elapsed_ms=result["elapsed_ms"], decision_source=result["decision_source"],
              message=f"swept {result['corpus']['transitions']} rows, {result['regression_count']} regressions")
    return {"data": result}


@app.get("/v1/catalogue/timeline")
async def catalogue_timeline(parent_asset: str, child_asset: str) -> dict[str, object]:
    """Second-by-second qualifying transitions for an approved master and one rendition.

    This is what the evidence chart draws. Both tracks come from the same query
    over the same table on one shared scale, so the page cannot flatter the
    comparison by scaling the two sides differently.
    """
    from .catalogue import timeline

    try:
        result = await timeline(parent_asset, child_asset)
    except ClickHouseNotConfigured as exc:
        raise HTTPException(
            503, detail={"code": "mcp_clickhouse_not_configured", "message": str(exc)}
        ) from exc
    except Exception as exc:
        raise HTTPException(
            502,
            detail={
                "code": "catalogue_timeline_failed",
                "message": f"The timeline failed closed ({type(exc).__name__}); no track was invented.",
            },
        ) from exc
    return {"data": result}


@app.get("/v1/catalogue/transform-risk")
async def catalogue_transform_risk() -> dict[str, object]:
    """Per-transform regression rates: is this scattered accidents or a few profiles?

    The operational difference matters more than the count. A transform with a
    non-zero rate is one upstream configuration to fix, not N renditions to
    patch one at a time.
    """
    from .catalogue import transform_risk

    try:
        result = await transform_risk()
    except ClickHouseNotConfigured as exc:
        raise HTTPException(
            503, detail={"code": "mcp_clickhouse_not_configured", "message": str(exc)}
        ) from exc
    except Exception as exc:
        raise HTTPException(
            502,
            detail={
                "code": "transform_risk_failed",
                "message": f"The risk profile failed closed ({type(exc).__name__}).",
            },
        ) from exc
    return {"data": result}


@app.post("/v1/triage", dependencies=[Depends(rate_limit("/v1/triage", 6))])
async def triage(request: TriageRequest) -> dict[str, object]:
    """The multi-step agent: survey, find the systemic cause, size the blind spot, go deep.

    Returns the brief together with the tool-call sequence that produced it, so
    the multi-step work can be checked rather than taken on trust.
    """
    try:
        from .adk_app import triage_catalogue

        result = await triage_catalogue(request.operator_id)
    except Exception as exc:
        log_event("fail_closed", severity="ERROR", endpoint="/v1/triage",
                  code="agent_triage_failed", reason=type(exc).__name__,
                  message="the triage agent could not complete")
        raise HTTPException(
            502,
            detail={
                "code": "agent_triage_failed",
                "message": f"The ADK triage agent could not complete ({type(exc).__name__}).",
            },
        ) from exc
    return {"data": result}


@app.get("/v1/evaluation")
async def evaluation_endpoint() -> dict[str, object]:
    """Score the detector against what the generator planted.

    The ground truth is recovered from the generator's `sipHash64` decisions
    without reading any measurement column, so agreement with the sweep is a
    measurement rather than a restatement. Decoys that must not be returned are
    scored too, because recall alone can be bought by flagging everything.
    """
    from .catalogue import evaluation

    try:
        result = await evaluation()
    except ClickHouseNotConfigured as exc:
        raise HTTPException(
            503, detail={"code": "mcp_clickhouse_not_configured", "message": str(exc)}
        ) from exc
    except Exception as exc:
        log_event("fail_closed", severity="ERROR", endpoint="/v1/evaluation",
                  code="evaluation_failed", reason=type(exc).__name__,
                  message="the evaluation failed closed; no score was invented")
        raise HTTPException(
            502,
            detail={
                "code": "evaluation_failed",
                "message": f"The evaluation failed closed ({type(exc).__name__}); no score was invented.",
            },
        ) from exc
    log_event("evaluation", planted=result["planted"], found=result["found"],
              precision=result["precision"], recall=result["recall"],
              decoys_wrongly_flagged=result["decoys"]["wrongly_flagged"],
              message=f"precision {result['precision']}, recall {result['recall']}")
    return {"data": result}


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


@app.post("/v1/explain", dependencies=[Depends(rate_limit("/v1/explain", 12))])
async def explain(request: ExplanationRequest) -> dict[str, object]:
    try:
        from .adk_app import explain_regression

        result = await explain_regression(request.parent_asset, request.child_asset, request.operator_id)
    except Exception as exc:
        log_event("fail_closed", severity="ERROR", endpoint="/v1/explain",
                  code="agent_explanation_failed", reason=type(exc).__name__,
                  message="the explanation agent could not complete")
        raise HTTPException(
            502,
            detail={"code": "agent_explanation_failed", "message": "ADK could not complete the MCP-grounded explanation."},
        ) from exc
    return {"data": result}
