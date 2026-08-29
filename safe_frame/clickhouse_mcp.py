from __future__ import annotations

import json
import os
import re
import shlex
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .mcp_worker import McpWorker


class ClickHouseNotConfigured(RuntimeError):
    pass


_ASSET_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")

# One persistent official-server session per distinct configuration.
_WORKERS: dict[tuple, McpWorker] = {}


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

    def _worker(self) -> McpWorker:
        """One persistent session per distinct server configuration."""
        key = (
            self.parameters.command,
            tuple(self.parameters.args),
            tuple(sorted((self.parameters.env or {}).items())),
        )
        worker = _WORKERS.get(key)
        if worker is None:
            worker = McpWorker(self.parameters)
            _WORKERS[key] = worker
        return worker

    async def tools(self) -> list[str]:
        return await self._worker().tools()

    async def query(self, sql: str) -> dict[str, Any]:
        results, _ = await self.query_many([sql])
        return results[0]

    async def query_many(self, statements: list[str]) -> tuple[list[dict[str, Any]], dict[str, float]]:
        """Run several statements over the persistent MCP session.

        The returned timing splits transport setup from execution so neither is
        misreported as the other. Once the session is warm `mcp_setup_ms` is the
        cost of confirming it is alive, not of spawning a new server.
        """
        worker = self._worker()
        timing: dict[str, float] = {}
        started = time.perf_counter()
        await worker.tools()
        timing["mcp_setup_ms"] = round((time.perf_counter() - started) * 1000, 1)
        query_started = time.perf_counter()
        collected = [await worker.query(sql) for sql in statements]
        timing["query_ms"] = round((time.perf_counter() - query_started) * 1000, 1)
        return collected, timing


PAIR_CRITERIA_SQL = """
general_flash_qualifying AS
(
    SELECT lineage_id, asset_id, parent_id, transform,
           pts_ms, changed_area_fraction, toUInt8(direction) AS dir
    FROM safe_frame.transitions
    WHERE asset_id IN ({assets})
      AND luma_delta >= 0.10
      AND changed_area_fraction >= 0.25
      AND direction != 'flat'
),
general_flash_windowed AS
(
    SELECT
        lineage_id, asset_id, parent_id, transform,
           pts_ms AS win_start,
        count() OVER w AS win_transitions,
        max(changed_area_fraction) OVER w AS win_peak_area,
        min(dir) OVER w AS win_dir_min,
        max(dir) OVER w AS win_dir_max
    FROM general_flash_qualifying
    WINDOW w AS (
        PARTITION BY asset_id
        ORDER BY pts_ms
        RANGE BETWEEN CURRENT ROW AND 999 FOLLOWING
    )
),
general_flash_measured AS
(
    SELECT
        toString(lineage_id) AS lineage_id,
        toString(asset_id) AS asset_id,
        toString(parent_id) AS parent_id,
        toString(transform) AS transform,
        'general_flash' AS rule,
        toUInt32(min(win_start)) AS window_start_ms,
        toUInt32(min(win_start) + 1000) AS window_end_ms,
        toUInt64(argMin(win_transitions, win_start)) AS transitions,
        toFloat64(argMin(win_peak_area, win_start)) AS peak_changed_area_fraction
    FROM general_flash_windowed
    WHERE win_transitions > 6
      AND win_dir_min != win_dir_max
    GROUP BY lineage_id, asset_id, parent_id, transform
),
red_flash_qualifying AS
(
    SELECT lineage_id, asset_id, parent_id, transform,
           pts_ms, changed_area_fraction, toUInt8(direction) AS dir
    FROM safe_frame.transitions
    WHERE asset_id IN ({assets})
      AND red_delta >= 0.20
      AND changed_area_fraction >= 0.25
      AND direction != 'flat'
),
red_flash_windowed AS
(
    SELECT
        lineage_id, asset_id, parent_id, transform,
           pts_ms AS win_start,
        count() OVER w AS win_transitions,
        max(changed_area_fraction) OVER w AS win_peak_area,
        min(dir) OVER w AS win_dir_min,
        max(dir) OVER w AS win_dir_max
    FROM red_flash_qualifying
    WINDOW w AS (
        PARTITION BY asset_id
        ORDER BY pts_ms
        RANGE BETWEEN CURRENT ROW AND 999 FOLLOWING
    )
),
red_flash_measured AS
(
    SELECT
        toString(lineage_id) AS lineage_id,
        toString(asset_id) AS asset_id,
        toString(parent_id) AS parent_id,
        toString(transform) AS transform,
        'red_flash' AS rule,
        toUInt32(min(win_start)) AS window_start_ms,
        toUInt32(min(win_start) + 1000) AS window_end_ms,
        toUInt64(argMin(win_transitions, win_start)) AS transitions,
        toFloat64(argMin(win_peak_area, win_start)) AS peak_changed_area_fraction
    FROM red_flash_windowed
    WHERE win_transitions > 6
      AND win_dir_min != win_dir_max
    GROUP BY lineage_id, asset_id, parent_id, transform
),
stored AS
(
    SELECT
        toString(lineage_id) AS lineage_id,
        toString(asset_id) AS asset_id,
        toString(parent_id) AS parent_id,
        toString(transform) AS transform,
        toString(rule) AS rule,
        toUInt32(window_start_ms) AS window_start_ms,
        toUInt32(window_end_ms) AS window_end_ms,
        toUInt64(transitions) AS transitions,
        toFloat64(peak_changed_area_fraction) AS peak_changed_area_fraction
    FROM safe_frame.violations FINAL
    WHERE asset_id IN ({assets})
),
evaluated AS
(
    SELECT * FROM general_flash_measured
    UNION ALL
    SELECT * FROM red_flash_measured
    UNION ALL
    SELECT * FROM stored
)
""".strip()



def regression_sql(parent_asset: str, child_asset: str, *, count_only: bool = False) -> str:
    """Child-minus-parent anti-join over one asset pair, evaluated in ClickHouse.

    A violation for a pair can exist in either of two places:

    * measured  -- the published criteria applied live to `safe_frame.transitions`,
                   which is where every catalogue rendition lives. This is the same
                   rule expression as `sql/006_catalogue_regression.sql`, scoped to
                   two assets instead of the whole corpus.
    * stored    -- rows already persisted to `safe_frame.violations` by `/v1/scan`,
                   which is where a pair submitted as raw metrics lives.

    Both must feed one verdict. Reading only `violations` made the per-pair
    endpoints answer "pass" for renditions the catalogue sweep had just flagged,
    because catalogue violations are never materialised. Unioning the two planes
    before the anti-join means the sweep, `/v1/catalogue/regressions` and
    `/v1/explain` cannot disagree about the same pair.

    The anti-join is keyed on `rule`, so a master that already flashed in
    luminance does not excuse a rendition that introduced a red flash.
    """
    parent = _asset(parent_asset)
    child = _asset(child_asset)
    assets = f"'{parent}', '{child}'"
    projection = (
        "count() AS regression_count"
        if count_only
        else "child.lineage_id AS lineage_id, child.asset_id AS asset_id, "
        "child.parent_id AS parent_id, child.transform AS transform, child.rule AS rule, "
        "child.window_start_ms AS window_start_ms, child.window_end_ms AS window_end_ms, "
        "child.transitions AS transitions, "
        "round(child.peak_changed_area_fraction, 4) AS peak_changed_area_fraction"
    )
    return f"""
WITH
{PAIR_CRITERIA_SQL.format(assets=assets)},
parent AS
(
    SELECT lineage_id, rule, window_start_ms
    FROM evaluated
    WHERE asset_id = '{parent}'
),
child AS
(
    SELECT * FROM evaluated WHERE asset_id = '{child}'
)
SELECT {projection}
FROM child
LEFT ANTI JOIN parent
    ON child.lineage_id = parent.lineage_id
   AND child.rule = parent.rule
   AND abs(toInt64(child.window_start_ms) - toInt64(parent.window_start_ms)) <= 100
{"" if count_only else "ORDER BY child.window_start_ms, child.rule"}
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


CRITERIA_SQL = """
general_flash_qualifying AS
(
    SELECT asset_id, pts_ms, changed_area_fraction, multiIf(direction = 'up', 1, direction = 'down', 2, 0) AS dir
    FROM src
    WHERE luma_delta >= 0.10
      AND changed_area_fraction >= 0.25
      AND direction != 'flat'
),
general_flash_windowed AS
(
    SELECT
        asset_id, pts_ms AS win_start,
        count() OVER w AS win_transitions,
        max(changed_area_fraction) OVER w AS win_peak_area,
        min(dir) OVER w AS win_dir_min,
        max(dir) OVER w AS win_dir_max
    FROM general_flash_qualifying
    WINDOW w AS (
        PARTITION BY asset_id
        ORDER BY pts_ms
        RANGE BETWEEN CURRENT ROW AND 999 FOLLOWING
    )
),
general_flash_violations AS
(
    SELECT asset_id, 'general_flash' AS rule,
           min(win_start) AS window_start_ms,
           min(win_start) + 1000 AS window_end_ms,
           argMin(win_transitions, win_start) AS transitions,
           argMin(win_peak_area, win_start) AS peak_changed_area_fraction
    FROM general_flash_windowed
    WHERE win_transitions > 6 AND win_dir_min != win_dir_max
    GROUP BY asset_id
),
red_flash_qualifying AS
(
    SELECT asset_id, pts_ms, changed_area_fraction, multiIf(direction = 'up', 1, direction = 'down', 2, 0) AS dir
    FROM src
    WHERE red_delta >= 0.20
      AND changed_area_fraction >= 0.25
      AND direction != 'flat'
),
red_flash_windowed AS
(
    SELECT
        asset_id, pts_ms AS win_start,
        count() OVER w AS win_transitions,
        max(changed_area_fraction) OVER w AS win_peak_area,
        min(dir) OVER w AS win_dir_min,
        max(dir) OVER w AS win_dir_max
    FROM red_flash_qualifying
    WINDOW w AS (
        PARTITION BY asset_id
        ORDER BY pts_ms
        RANGE BETWEEN CURRENT ROW AND 999 FOLLOWING
    )
),
red_flash_violations AS
(
    SELECT asset_id, 'red_flash' AS rule,
           min(win_start) AS window_start_ms,
           min(win_start) + 1000 AS window_end_ms,
           argMin(win_transitions, win_start) AS transitions,
           argMin(win_peak_area, win_start) AS peak_changed_area_fraction
    FROM red_flash_windowed
    WHERE win_transitions > 6 AND win_dir_min != win_dir_max
    GROUP BY asset_id
),
violations AS
(
    SELECT * FROM general_flash_violations
    UNION ALL
    SELECT * FROM red_flash_violations
)
""".strip()



def _sql_string(value: str) -> str:
    if "\\" in value or "'" in value:
        raise ValueError("identifiers used in inline parity fixtures may not contain quotes")
    return f"'{value}'"


def parity_sql(rows: list[dict[str, Any]]) -> str:
    """Apply the published criteria to an inline dataset.

    Used by tests/test_sql_parity.py to run the exact ClickHouse window
    evaluation over the same rows the reference Python detector sees, through
    the same read-only MCP transport the product uses. Both rules are evaluated,
    so a fixture that trips one and not the other is checked too. No table is
    written, so the SELECT-only MCP user can execute it.
    """
    if not rows:
        raise ValueError("parity_sql needs at least one row")
    literals = []
    for row in rows:
        if row["direction"] not in ("up", "down", "flat"):
            raise ValueError(f"unknown direction {row['direction']!r}")
        literals.append(
            "({asset}, {pts}, {luma}, {red}, {area}, {direction})".format(
                asset=_sql_string(str(row["asset_id"])),
                pts=int(row["pts_ms"]),
                luma=float(row["luma_delta"]),
                red=float(row.get("red_delta", 0.0)),
                area=float(row["changed_area_fraction"]),
                direction=_sql_string(str(row["direction"])),
            )
        )
    values = ",\n        ".join(literals)
    return f"""
WITH
src AS
(
    SELECT * FROM VALUES(
        'asset_id String, pts_ms UInt32, luma_delta Float64, red_delta Float64, changed_area_fraction Float64, direction String',
        {values}
    )
),
{CRITERIA_SQL}
SELECT asset_id, rule, window_start_ms, window_end_ms, transitions,
       round(peak_changed_area_fraction, 6) AS peak_changed_area_fraction
FROM violations
ORDER BY asset_id, rule
""".strip()


async def parity_violations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run the criteria SQL through official mcp-clickhouse and decode the rows."""
    result = await ClickHouseMcp().query(parity_sql(rows))
    if result["is_error"]:
        raise RuntimeError(f"mcp-clickhouse returned an error: {result['content']}")
    text = "\n".join(str(item.get("text", "")) for item in result["content"])
    decoded = json.loads(text) if text.strip().startswith(("{", "[")) else text
    if isinstance(decoded, str):
        decoded = json.loads(decoded)
    if isinstance(decoded, dict) and "rows" in decoded and "columns" in decoded:
        columns = list(decoded["columns"])
        return [dict(zip(columns, row)) for row in decoded["rows"]]
    if isinstance(decoded, list):
        return decoded
    if isinstance(decoded, dict):
        return [decoded]
    raise RuntimeError(f"unexpected parity payload: {text[:400]}")


def timeline_sql(parent_asset: str, child_asset: str) -> str:
    """Per-second qualifying-transition counts for an approved master and one rendition.

    The sweep answers *which* renditions regressed. This answers *what the
    difference looks like*: for every second of both assets, how many
    transitions actually counted toward each rule. Plotting the two tracks on
    one shared scale is the claim itself -- the master stays under the
    criterion for the whole runtime while the rendition spikes past it in one
    second -- drawn from measurements rather than asserted in prose.

    Seconds with no qualifying transitions are kept, so the baseline is visible
    and a reader can see the burst is an exception rather than the shape of the
    whole asset.
    """
    parent = _asset(parent_asset)
    child = _asset(child_asset)
    return f"""
SELECT
    asset_id,
    toUInt32(intDiv(pts_ms, 1000)) AS second,
    countIf(luma_delta >= 0.10
            AND changed_area_fraction >= 0.25
            AND direction != 'flat') AS general_flash,
    countIf(red_delta >= 0.20
            AND changed_area_fraction >= 0.25
            AND direction != 'flat') AS red_flash
FROM safe_frame.transitions
WHERE asset_id IN ('{parent}', '{child}')
GROUP BY asset_id, second
ORDER BY asset_id, second
""".strip()
