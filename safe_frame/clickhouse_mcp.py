from __future__ import annotations

import json
import os
import re
import shlex
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class ClickHouseNotConfigured(RuntimeError):
    pass


_ASSET_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ClickHouseNotConfigured(f"{name} is required")
    return value


def _asset(value: str) -> str:
    if not _ASSET_ID.fullmatch(value):
        raise ValueError("asset IDs may contain only letters, numbers, underscores, and hyphens")
    return value


class ClickHouseMcp:
    """Read-only access through the official ClickHouse MCP server."""

    def __init__(self) -> None:
        command = _required("MCP_CLICKHOUSE_COMMAND")
        parts = shlex.split(command, posix=os.name != "nt")
        allowed = (
            "CLICKHOUSE_HOST", "CLICKHOUSE_PORT", "CLICKHOUSE_USER", "CLICKHOUSE_PASSWORD",
            "CLICKHOUSE_DATABASE", "CLICKHOUSE_SECURE", "CLICKHOUSE_VERIFY",
            "CLICKHOUSE_CONNECT_TIMEOUT", "CLICKHOUSE_SEND_RECEIVE_TIMEOUT",
            "CLICKHOUSE_MCP_QUERY_TIMEOUT", "CLICKHOUSE_MCP_SERVER_TRANSPORT",
        )
        child_env = {name: value for name in allowed if (value := os.getenv(name))}
        child_env["CLICKHOUSE_ALLOW_WRITE_ACCESS"] = "false"
        child_env["CLICKHOUSE_ALLOW_DROP"] = "false"
        self.parameters = StdioServerParameters(command=parts[0], args=parts[1:], env=child_env)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[ClientSession]:
        async with stdio_client(self.parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    async def tools(self) -> list[str]:
        async with self.session() as session:
            result = await session.list_tools()
        return sorted(tool.name for tool in result.tools)

    async def query(self, sql: str) -> dict[str, Any]:
        async with self.session() as session:
            advertised = await session.list_tools()
            names = {tool.name for tool in advertised.tools}
            if "run_query" not in names:
                raise RuntimeError(f"official mcp-clickhouse did not advertise run_query: {sorted(names)}")
            result = await session.call_tool("run_query", {"query": sql})
        return {
            "tool": "run_query",
            "is_error": bool(getattr(result, "isError", False)),
            "content": [item.model_dump() for item in result.content],
        }


def regression_sql(parent_asset: str, child_asset: str, *, count_only: bool = False) -> str:
    parent = _asset(parent_asset)
    child = _asset(child_asset)
    projection = "count() AS regression_count" if count_only else "child.*"
    return f"""
WITH parent AS
(
    SELECT lineage_id, rule, window_start_ms
    FROM safe_frame.violations FINAL
    WHERE asset_id = '{parent}'
),
child AS
(
    SELECT lineage_id, asset_id, parent_id, transform, rule, window_start_ms,
           window_end_ms, transitions, peak_changed_area_fraction
    FROM safe_frame.violations FINAL
    WHERE asset_id = '{child}'
)
SELECT {projection}
FROM child
LEFT ANTI JOIN parent
    ON child.lineage_id = parent.lineage_id
   AND child.rule = parent.rule
   AND abs(toInt64(child.window_start_ms) - toInt64(parent.window_start_ms)) <= 100
{"" if count_only else "ORDER BY child.window_start_ms"}
""".strip()


async def catalogue_regression_evidence(parent_asset: str, child_asset: str) -> dict[str, Any]:
    """Read child-only safety violations from ClickHouse through official MCP."""

    return await ClickHouseMcp().query(regression_sql(parent_asset, child_asset))


async def regression_count(parent_asset: str, child_asset: str) -> tuple[int, dict[str, Any]]:
    result = await ClickHouseMcp().query(regression_sql(parent_asset, child_asset, count_only=True))
    if result["is_error"]:
        raise RuntimeError("mcp-clickhouse returned an error")
    text = "\n".join(str(item.get("text", "")) for item in result["content"])
    try:
        decoded = json.loads(text)
        if isinstance(decoded, str):
            decoded = json.loads(decoded)
        if isinstance(decoded, dict) and "regression_count" in decoded:
            return int(decoded["regression_count"]), result
        if isinstance(decoded, dict) and decoded.get("columns") and decoded.get("rows"):
            index = list(decoded["columns"]).index("regression_count")
            return int(decoded["rows"][0][index]), result
    except (json.JSONDecodeError, TypeError, ValueError, IndexError, KeyError):
        pass
    match = re.search(r'"regression_count"\s*:\s*"?(\d+)', text)
    if not match:
        # Some MCP versions wrap the JSON row in an encoded JSON string.
        match = re.search(r'"regression_count"\s*:\s*"?(\d+)', json.dumps(text))
    if not match:
        raise RuntimeError("could not parse deterministic regression_count from mcp-clickhouse")
    return int(match.group(1)), result
