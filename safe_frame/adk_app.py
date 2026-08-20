from __future__ import annotations

import os
import uuid

from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .clickhouse_mcp import catalogue_regression_evidence


MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
APP_NAME = "safe_frame"

async def explain_regression(parent_asset: str, child_asset: str, operator_id: str) -> dict[str, object]:
    async def get_bound_catalogue_evidence() -> dict[str, object]:
        """Return MCP evidence for the validated asset pair bound to this request."""

        return await catalogue_regression_evidence(parent_asset, child_asset)

    root_agent = LlmAgent(
        name="RegressionExplainer",
        model=MODEL,
        instruction=(
            "You explain a deterministic master-to-rendition photosensitivity pre-check. "
            "You MUST call get_bound_catalogue_evidence exactly once; it is securely bound to "
            "the validated pair and accepts no arguments. Never invent a verdict, never call "
            "this certified, and never recommend exposing a viewer to offending frames. Cite "
            "timecodes, rule, affected area, and transform only when present in the ClickHouse "
            "MCP result. End with a human QC action."
        ),
        tools=[get_bound_catalogue_evidence],
    )
    service = InMemorySessionService()
    session_id = f"safe_frame_{uuid.uuid4().hex[:12]}"
    await service.create_session(app_name=APP_NAME, user_id=operator_id, session_id=session_id)
    runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=service)
    message = types.Content(
        role="user",
        parts=[types.Part(text=f"Explain child {child_asset} against approved parent {parent_asset}.")],
    )
    transcript: list[str] = []
    async for event in runner.run_async(user_id=operator_id, session_id=session_id, new_message=message):
        for part in getattr(getattr(event, "content", None), "parts", None) or []:
            if getattr(part, "text", None):
                transcript.append(part.text)
    return {
        "status": "completed",
        "agent": "RegressionExplainer",
        "model": MODEL,
        "decision_source": "clickhouse_sql",
        "evidence_transport": "official_mcp_clickhouse_stdio",
        "requires_human": True,
        "text": transcript[-1] if transcript else "",
    }
