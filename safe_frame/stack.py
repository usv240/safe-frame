"""What this service is built from, and which parts are answering right now.

A status dot is worth nothing if it is decorative, so this reports three honest
states rather than painting everything green:

    live        a round trip completed just now. ClickHouse returned its version
                string, the official MCP server listed its tools, Vertex
                answered. These are the only ones that prove a remote system is
                reachable.
    active      in use inside the process serving this request, and provable
                from it: the Cloud Run revision serving you, the ADK version
                imported, the library doing the measurement.
    applied     used to build the thing but not part of the request path, such
                as the ClickHouse Agent Skills and the browser checks in CI.
                Marking these live would be a lie.

Each entry also carries `how`, which is the part a reader actually wants: not
that we used ClickHouse, but what we asked it to do.
"""

from __future__ import annotations

import os
from importlib import metadata
from typing import Any


def _version(distribution: str) -> str | None:
    try:
        return metadata.version(distribution)
    except Exception:
        return None


def _entry(
    key: str,
    name: str,
    group: str,
    role: str,
    how: str,
    status: str,
    *,
    version: str | None = None,
    evidence: str | None = None,
    depth: str | None = None,
    reference: str | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "name": name,
        "group": group,
        "role": role,
        "how": how,
        "status": status,
        "version": version,
        "evidence": evidence,
        "depth": depth,
        "reference": reference,
    }


def build_stack(
    *,
    clickhouse_live: bool,
    vertex_live: bool,
    clickhouse_version: str | None = None,
    mcp_tools: list[str] | None = None,
) -> dict[str, Any]:
    """Describe the stack, with live results folded in where they were obtained."""
    revision = os.getenv("K_REVISION")
    on_cloud_run = bool(revision)
    tools = mcp_tools or []

    components = [
        _entry(
            "clickhouse",
            f"ClickHouse {clickhouse_version or '26.3 LTS'}",
            "partner",
            "Every verdict on this site is a ClickHouse result.",
            "The published flash criteria are implemented as SQL and evaluated across the "
            "whole catalogue in one pass: two rules, each windowed over its own qualifying "
            "set, then a child-minus-parent isolation so only violations the master lacked "
            "are returned.",
            "live" if clickhouse_live else "unreachable",
            version=clickhouse_version,
            evidence="version string read live through the official MCP server",
            depth="MergeTree ordered by (lineage_id, asset_id, pts_ms) with LowCardinality "
            "and Enum8 columns. The 1000 ms window is a RANGE BETWEEN CURRENT ROW AND 999 "
            "FOLLOWING over presentation time, never frame index, because a frame-rate "
            "conversion renumbers every frame. Isolation uses a partition window rather "
            "than a self anti-join, measured at 791 ms against 2,274 ms.",
            reference="sql/006_catalogue_regression.sql",
        ),
        _entry(
            "mcp",
            "Official ClickHouse MCP server (mcp-clickhouse)",
            "partner",
            "The only route from this service to the database for reads.",
            "Started as a read-only stdio subprocess with write and drop access disabled. "
            "Every catalogue read, every live verdict and every agent tool call goes "
            "through it. The child process is handed ClickHouse credentials and nothing "
            "else, so it cannot reach Google credentials.",
            "live" if clickhouse_live else "unreachable",
            version=_version("mcp-clickhouse"),
            evidence=f"advertised tools listed live: {', '.join(tools)}" if tools else None,
            depth="One long-lived session per event loop rather than a subprocess per "
            "request, which removes 4 to 8 seconds of handshake from every call. The "
            "session is owned by a single task and fed over a queue, because the MCP "
            "client builds on anyio task groups and a session entered in one task and "
            "used from another raises cancel-scope errors.",
            reference="safe_frame/mcp_worker.py",
        ),
        _entry(
            "skills",
            "ClickHouse Agent Skills",
            "partner",
            "The vendor's own rules, applied to our schema and queries.",
            "All 31 official rules were worked through against this project. Most were "
            "applied; four were declined with measurements showing why, including one "
            "CRITICAL rule where the recommended single-scan shape measured 27 percent "
            "slower on our data than the two-pass form we ship.",
            "applied",
            evidence="development-time, not part of the request path",
            depth="The interesting decline is query-join-consider-alternatives. Two passes "
            "over 9.6M rows should read 19.2M; they read 10.26M, because per-granule "
            "min/max lets ClickHouse skip about 93 percent of the second scan.",
            reference="docs/CLICKHOUSE-SKILLS-REVIEW.md",
        ),
        _entry(
            "refreshable_mv",
            "Refreshable materialized view",
            "partner",
            "Built, measured, and deliberately switched off.",
            "ClickHouse's own guidance (query-mv-refreshable, impact HIGH) says a fixed "
            "answer that many people reload should not be re-derived per request. The "
            "view exists and works: 44 rows in 5.9ms against 10,263,552 rows in 932ms "
            "for the same output, about 158 times faster.",
            "declined",
            evidence="not created on the deployed cluster, on purpose",
            depth="This page claims that nothing on it is a pre-computed answer: press "
            "the button and the criteria are evaluated in front of you, with the elapsed "
            "time reported. Serving that button from a view refreshed five minutes ago "
            "would make the demonstration a lookup and the claim false. Five minutes of "
            "staleness is right for an operations dashboard and wrong for \"this was "
            "computed just now\". The DDL ships so a real deployment can create it in "
            "one statement; this one keeps paying the 932ms on purpose.",
            reference="sql/007_refreshable_regressions.sql",
        ),
        _entry(
            "gemini",
            f"Gemini 2.5 Flash on Vertex AI ({os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')})",
            "google",
            "Explains database evidence. Decides nothing.",
            "Two agents. RegressionExplainer is single-step and bound to one validated "
            "pair. QcTriageAgent is multi-step: it surveys the sweep, profiles every "
            "transform to find the systemic cause, sizes the luminance blind spot, then "
            "goes deep on the finding it ranks first, and writes the brief.",
            "live" if vertex_live else "unreachable",
            evidence="a live Vertex round trip completed within the last minute",
            depth="Every tool is a read-only ClickHouse query through MCP, so the model "
            "cannot obtain a number except from SQL. The tool sequence is recorded during "
            "the run and returned with the brief, and the response carries "
            "decision_source=clickhouse_sql with requires_human=true. If the MCP path "
            "fails the API returns 502 rather than substituting a model answer.",
            reference="safe_frame/adk_app.py",
        ),
        _entry(
            "adk",
            "Google Agent Development Kit",
            "google",
            "The agent runtime.",
            "LlmAgent plus Runner, with the four triage tools declared as Python functions "
            "and executed through the ADK event loop. Tool calls are read off the event "
            "stream as they happen, which is how the numbered trace on this page is "
            "recorded rather than asserted.",
            "active" if on_cloud_run else "configured",
            version=_version("google-adk"),
            evidence="imported and serving in this process",
            reference="safe_frame/adk_app.py",
        ),
        _entry(
            "cloudrun",
            "Cloud Run",
            "google",
            "Serving this response.",
            "A container on a dedicated safe-frame-runtime service identity, with a warm "
            "instance so the first sweep a judge presses is not paying a cold start on top "
            "of an MCP handshake.",
            "active" if on_cloud_run else "configured",
            version=revision,
            evidence=f"revision {revision} is serving this request" if revision else None,
            reference="Dockerfile",
        ),
        _entry(
            "secrets",
            "Secret Manager",
            "google",
            "Holds every credential this service uses.",
            "ClickHouse passwords and the API-key signing secret are mounted as secret "
            "references, never baked into the image and never committed. The MCP "
            "subprocess receives only the ClickHouse variables.",
            "active"
            if os.getenv("CLICKHOUSE_PASSWORD") and os.getenv("SAFE_FRAME_API_KEY_SECRET")
            else "configured",
            evidence="secret-backed environment is present in this process",
            reference="SECURITY.md",
        ),
        _entry(
            "logging",
            "Cloud Logging",
            "google",
            "Makes the agent's work reconstructable after the fact.",
            "Every agent run and every fail-closed refusal emits a structured entry that "
            "Cloud Logging lifts into jsonPayload, recording which tools ran in what order "
            "and that the decision stayed with SQL. No submitted data and no model prose "
            "is ever logged.",
            "active",
            evidence="structured entries are written on stdout by this process",
            reference="safe_frame/telemetry.py",
        ),
        _entry(
            "fastapi",
            "FastAPI",
            "app",
            "The API surface, and the OpenAPI document at /docs.",
            "Pydantic models validate every submission before it reaches the measurement "
            "stage, which is why a malformed frame buffer is refused with a reason rather "
            "than measured as a shorter clip.",
            "active",
            version=_version("fastapi"),
            evidence="serving this request",
        ),
        _entry(
            "numpy",
            "NumPy",
            "app",
            "The measurement stage.",
            "Frames are measured into transition rows: relative luminance is linearised "
            "from sRGB before the BT.709 coefficients, and the published saturated-red "
            "test runs per pixel. The step and the affected area are recorded separately, "
            "because the criteria test them independently.",
            "active",
            version=_version("numpy"),
            evidence="the same code path measured the catalogue and measures your clip",
            reference="safe_frame/ingest.py",
        ),
        _entry(
            "playwright",
            "Playwright",
            "app",
            "Proves the page works, not just that it renders.",
            "A real browser drives the judge path at phone, laptop and desktop widths in "
            "both themes, and fails on horizontal overflow or any console error. It exists "
            "because a script that throws at init detaches every listener while every "
            "assertion about page content still passes, which happened twice.",
            "applied",
            version=_version("playwright"),
            evidence="runs in CI on every commit",
            reference="scripts/visual_check.py",
        ),
        _entry(
            "pytest",
            "pytest",
            "app",
            "Including the one test that keeps two implementations honest.",
            "83 tests. The parity suite runs the reference Python detector and the "
            "ClickHouse SQL over identical randomised rows and requires exact agreement on "
            "both rules, through the real MCP transport.",
            "applied",
            version=_version("pytest"),
            evidence="a throwaway ClickHouse is stood up in CI and the job fails if the "
            "parity tests skip",
            reference="tests/test_sql_parity.py",
        ),
    ]
    return {
        "components": components,
        "summary": {
            "live": sum(1 for c in components if c["status"] == "live"),
            "active": sum(1 for c in components if c["status"] == "active"),
            "applied": sum(1 for c in components if c["status"] == "applied"),
            "declined": sum(1 for c in components if c["status"] == "declined"),
            "unreachable": sum(1 for c in components if c["status"] == "unreachable"),
        },
        "legend": {
            "live": "a round trip to a remote system completed just now",
            "active": "in use in the process serving this request",
            "applied": "used to build or verify this project, not part of the request path",
            "declined": "available and understood, and not used, for a stated reason",
            "unreachable": "configured but not answering right now",
        },
    }
