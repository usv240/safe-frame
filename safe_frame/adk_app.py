"""Google ADK agents over ClickHouse evidence retrieved through official MCP.

Two agents, both bound by the same rule: **every number they say has to have
come back from a ClickHouse query.** They orchestrate and narrate; the SQL
decides. Neither can reach a verdict of its own, and both end by handing the
decision to a human.

`RegressionExplainer` is single-step: one validated pair, one tool, one
explanation. It answers "what happened to this rendition?"

`QcTriageAgent` is the multi-step one, and it answers the question a QC lead
actually has at 9am: *forty-four findings — what do I do first, and why is this
happening?* It has four tools over the same read-only MCP transport and has to
sequence them itself:

    1. survey the sweep                 what regressed, and how much
    2. profile the transforms           is this scattered accidents or a few
                                        encoder profiles (the root cause)
    3. count the luminance blind spot   how many would a general-flash-only
                                        checker have missed entirely
    4. inspect one pair's timeline      evidence depth on the case it ranks first

Each tool is a real query through the official `mcp-clickhouse` server. The
tool-call sequence is recorded and returned, so the multi-step work is visible
rather than asserted -- a reader can see which tools ran, in what order, and
check the brief against them.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .clickhouse_mcp import catalogue_regression_evidence


MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
APP_NAME = "safe_frame"

_BOUNDARY = (
    "You are reporting on a deterministic photosensitivity pre-check. Every number "
    "you state must come from a tool result; if a tool did not return it, do not say "
    "it. Never call this certified, never declare anything safe, and never recommend "
    "exposing a viewer to offending frames. Always end with the human QC action."
)


async def _run(agent: LlmAgent, operator_id: str, prompt: str) -> dict[str, Any]:
    """Run one agent turn and record which tools it actually called."""
    service = InMemorySessionService()
    session_id = f"safe_frame_{uuid.uuid4().hex[:12]}"
    await service.create_session(app_name=APP_NAME, user_id=operator_id, session_id=session_id)
    runner = Runner(app_name=APP_NAME, agent=agent, session_service=service)

    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    transcript: list[str] = []
    trace: list[dict[str, Any]] = []
    async for event in runner.run_async(
        user_id=operator_id, session_id=session_id, new_message=message
    ):
        for part in getattr(getattr(event, "content", None), "parts", None) or []:
            call = getattr(part, "function_call", None)
            if call is not None and getattr(call, "name", None):
                trace.append({"step": len(trace) + 1, "tool": call.name})
            if getattr(part, "text", None):
                transcript.append(part.text)
    return {"text": transcript[-1] if transcript else "", "tool_calls": trace}


async def explain_regression(parent_asset: str, child_asset: str, operator_id: str) -> dict[str, object]:
    async def get_bound_catalogue_evidence() -> dict[str, object]:
        """Return MCP evidence for the validated asset pair bound to this request."""

        return await catalogue_regression_evidence(parent_asset, child_asset)

    agent = LlmAgent(
        name="RegressionExplainer",
        model=MODEL,
        instruction=(
            "You explain a deterministic master-to-rendition photosensitivity pre-check. "
            "You MUST call get_bound_catalogue_evidence exactly once; it is securely bound "
            "to the validated pair and accepts no arguments. Cite timecodes, rule, affected "
            "area and transform only when present in the ClickHouse MCP result. " + _BOUNDARY
        ),
        tools=[get_bound_catalogue_evidence],
    )
    result = await _run(
        agent, operator_id, f"Explain child {child_asset} against approved parent {parent_asset}."
    )
    return {
        "status": "completed",
        "agent": "RegressionExplainer",
        "model": MODEL,
        "decision_source": "clickhouse_sql",
        "evidence_transport": "official_mcp_clickhouse_stdio",
        "requires_human": True,
        "tool_calls": result["tool_calls"],
        "text": result["text"],
    }


async def triage_catalogue(operator_id: str) -> dict[str, object]:
    """Multi-step: survey, find the systemic cause, size the blind spot, go deep on one."""
    from .catalogue import sweep, timeline, transform_risk

    used: list[str] = []
    seen: dict[str, Any] = {}

    async def survey_regressions() -> dict[str, Any]:
        """List every rendition in the catalogue that introduced a violation its master lacked.

        Returns the regressions with their rule, transform and window, plus the
        size of the corpus they were isolated from. Call this first.
        """
        used.append("survey_regressions")
        result = await sweep()
        seen["regressions"] = result["regressions"]
        return {
            "regression_count": result["regression_count"],
            "affected_titles": result["affected_titles"],
            "by_rule": result["by_rule"],
            "by_transform": result["by_transform"],
            "corpus": result["corpus"],
            "regressions": result["regressions"][:50],
        }

    async def profile_transform_risk() -> dict[str, Any]:
        """Per-transform regression rates across the catalogue: the systemic view.

        For every transform, how many renditions it produced, how many of those
        introduced a violation, the rate, and the split by rule. Use this to say
        whether the findings are scattered accidents or a few encoder profiles.
        """
        used.append("profile_transform_risk")
        result = await transform_risk()
        seen["risk"] = result
        return result

    async def count_luminance_blind_spot() -> dict[str, Any]:
        """How many regressions a general-flash-only checker would have missed.

        A saturated-red alternation can hold luminance under the general-flash
        floor. Regressions found only by the red rule are invisible to a
        luminance-only check.
        """
        used.append("count_luminance_blind_spot")
        risk = seen.get("risk") or await transform_risk()
        seen["risk"] = risk
        red_only = [
            p for p in risk["profiles"] if p["red_flash"] and not p["general_flash"]
        ]
        return {
            "red_only_regressions": sum(p["red_flash"] for p in red_only),
            "total_regressions": risk["total_regressed"],
            "transforms_producing_red_only": [p["transform"] for p in red_only],
            "why": (
                "these renditions hold luminance under the general-flash floor, so a "
                "checker implementing only the luminance rule passes them"
            ),
        }

    async def inspect_pair_timeline(child_asset: str) -> dict[str, Any]:
        """Second-by-second qualifying transitions for one rendition and its master.

        Pass the `asset_id` of a rendition from survey_regressions. Use this on
        the single finding you rank first, to show what the difference looks
        like rather than only that it exists.
        """
        used.append("inspect_pair_timeline")
        match = next(
            (r for r in seen.get("regressions", []) if r.get("asset_id") == child_asset), None
        )
        if match is None:
            return {"error": f"{child_asset} is not in the regression set; call survey_regressions first"}
        data = await timeline(str(match["parent_id"]), child_asset)
        return {
            "child": child_asset,
            "parent": match["parent_id"],
            "criterion_transitions_per_second": data["criterion_transitions_per_second"],
            "master_peak": max(
                max(data["parent"]["general_flash"] or [0]), max(data["parent"]["red_flash"] or [0])
            ),
            "rendition_peak": max(
                max(data["child"]["general_flash"] or [0]), max(data["child"]["red_flash"] or [0])
            ),
            "rendition_general_flash_peak": max(data["child"]["general_flash"] or [0]),
            "seconds": data["child"]["seconds"],
        }

    agent = LlmAgent(
        name="QcTriageAgent",
        model=MODEL,
        instruction=(
            "You are preparing the morning QC triage brief for a distribution team that "
            "is about to ship a catalogue.\n\n"
            "Work in this order, calling every tool at least once:\n"
            "1. survey_regressions - establish what regressed and how much.\n"
            "2. profile_transform_risk - decide whether these are scattered accidents or "
            "a small number of encoder profiles. Name the profiles and their rates.\n"
            "3. count_luminance_blind_spot - state how many findings a luminance-only "
            "checker would have missed, and why.\n"
            "4. inspect_pair_timeline - pick the single finding you would review first, "
            "pass its asset_id, and use the returned peaks as evidence.\n\n"
            "Then write the brief with these headings exactly: 'What the sweep found', "
            "'Systemic cause', 'What a luminance-only check would have missed', "
            "'Review first', 'Required human action'.\n"
            "Prefer the upstream fix: if one transform accounts for many regressions, say "
            "that fixing that profile is one action rather than N. Keep it under 300 words. "
            + _BOUNDARY
        ),
        tools=[
            survey_regressions,
            profile_transform_risk,
            count_luminance_blind_spot,
            inspect_pair_timeline,
        ],
    )
    result = await _run(
        agent,
        operator_id,
        "Prepare the QC triage brief for this catalogue before it ships.",
    )
    return {
        "status": "completed",
        "agent": "QcTriageAgent",
        "model": MODEL,
        "decision_source": "clickhouse_sql",
        "evidence_transport": "official_mcp_clickhouse_stdio",
        "requires_human": True,
        "tools_available": [
            "survey_regressions",
            "profile_transform_risk",
            "count_luminance_blind_spot",
            "inspect_pair_timeline",
        ],
        "tool_calls": result["tool_calls"],
        "steps": len(result["tool_calls"]),
        "text": result["text"],
    }
