import asyncio

import pytest

from safe_frame import clickhouse_mcp


def test_asset_ids_are_validated_before_sql():
    with pytest.raises(ValueError, match="asset IDs"):
        clickhouse_mcp.regression_sql("master'; DROP TABLE violations; --", "child")


def test_regression_query_uses_presentation_time_anti_join():
    sql = clickhouse_mcp.regression_sql("master", "social_60fps")
    assert "LEFT ANTI JOIN" in sql
    assert "window_start_ms" in sql
    assert "frame_idx" not in sql
    # mcp-clickhouse owns result formatting and appends ``FORMAT Native``.
    assert "FORMAT" not in sql
    assert not sql.rstrip().endswith(";")


def test_mcp_subprocess_is_read_only_and_gets_only_clickhouse_env(monkeypatch):
    monkeypatch.setenv("MCP_CLICKHOUSE_COMMAND", "mcp-clickhouse")
    monkeypatch.setenv("CLICKHOUSE_HOST", "clickhouse.example")
    monkeypatch.setenv("CLICKHOUSE_USER", "reader")
    monkeypatch.setenv("CLICKHOUSE_PASSWORD", "secret")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "must-not-leak")
    env = clickhouse_mcp.ClickHouseMcp().parameters.env
    assert env["CLICKHOUSE_ALLOW_WRITE_ACCESS"] == "false"
    assert env["CLICKHOUSE_ALLOW_DROP"] == "false"
    assert "GOOGLE_CLOUD_PROJECT" not in env


def test_regression_count_fails_closed_when_mcp_result_cannot_be_parsed(monkeypatch):
    async def fake_query(self, sql):
        return {"is_error": False, "content": [{"type": "text", "text": "not a count"}]}

    monkeypatch.setenv("MCP_CLICKHOUSE_COMMAND", "mcp-clickhouse")
    monkeypatch.setattr(clickhouse_mcp.ClickHouseMcp, "query", fake_query)
    with pytest.raises(RuntimeError, match="could not parse"):
        asyncio.run(clickhouse_mcp.regression_count("master", "child"))


def test_regression_count_parses_official_mcp_columns_and_rows(monkeypatch):
    async def fake_query(self, sql):
        return {
            "is_error": False,
            "content": [
                {"type": "text", "text": '{"columns":["regression_count"],"rows":[[1]]}'}
            ],
        }

    monkeypatch.setenv("MCP_CLICKHOUSE_COMMAND", "mcp-clickhouse")
    monkeypatch.setattr(clickhouse_mcp.ClickHouseMcp, "query", fake_query)
    count, _ = asyncio.run(clickhouse_mcp.regression_count("master", "child"))
    assert count == 1
