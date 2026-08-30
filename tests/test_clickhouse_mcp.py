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


def test_pair_verdict_reads_both_the_catalogue_and_persisted_planes():
    """A pair verdict must not depend on which surface created the violation.

    Catalogue renditions exist only as measurements in `safe_frame.transitions`
    and are never materialised into `safe_frame.violations`; pairs submitted to
    `/v1/scan` exist only in `violations`. Reading one table made the per-pair
    endpoints answer "pass" for renditions the catalogue sweep had just flagged.
    """
    sql = clickhouse_mcp.regression_sql("title_0017__master", "title_0017__60fps_interp")
    assert "safe_frame.transitions" in sql, "catalogue plane must be evaluated"
    assert "safe_frame.violations" in sql, "persisted plane must be included"
    assert "UNION ALL" in sql
    # Both planes must be unioned *before* the anti-join, or a parent violation
    # in one plane could not suppress a child violation in the other.
    assert sql.index("UNION ALL") < sql.index("LEFT ANTI JOIN")


def test_pair_criteria_match_the_reference_detector_thresholds():
    """The per-pair SQL must apply the same published criteria as the detector."""
    from safe_frame.detector import detect_general_flashes
    import inspect

    signature = inspect.signature(detect_general_flashes)
    sql = clickhouse_mcp.regression_sql("master", "child")
    assert f">= {signature.parameters['luma_delta_floor'].default:.2f}" in sql
    assert f">= {signature.parameters['area_floor'].default:.2f}" in sql
    assert f"> {signature.parameters['max_transitions_per_second'].default}" in sql
    assert "RANGE BETWEEN CURRENT ROW AND 999 FOLLOWING" in sql


def test_catalogue_sweep_sql_uses_the_same_published_criteria():
    """`sql/006` is what the sweep runs; it must not drift from the detector.

    `tests/test_sql_parity.py` proves behavioural agreement but needs a live
    ClickHouse. This structural check runs everywhere, including CI without
    cluster credentials, so a threshold edit cannot land unnoticed.
    """
    import inspect
    from pathlib import Path

    from safe_frame.detector import detect_general_flashes

    sql = (Path(__file__).resolve().parent.parent / "sql" / "006_catalogue_regression.sql").read_text(
        encoding="utf-8"
    )
    defaults = inspect.signature(detect_general_flashes).parameters
    assert f"luma_delta >= {defaults['luma_delta_floor'].default:.2f}" in sql
    assert f"changed_area_fraction >= {defaults['area_floor'].default:.2f}" in sql
    assert f"win_transitions > {defaults['max_transitions_per_second'].default}" in sql
    assert "RANGE BETWEEN CURRENT ROW AND 999 FOLLOWING" in sql
    assert "frame_idx" not in sql, "lineage alignment must use presentation time"


def test_the_darker_image_ceiling_is_applied_wherever_general_flash_is():
    """The condition an audit found missing must not go missing again.

    It belongs to the general-flash rule only: the published red-flash test
    carries no luminance condition at all.
    """
    from pathlib import Path

    pair = clickhouse_mcp.regression_sql("master", "child")
    sweep = (Path(__file__).resolve().parent.parent / "sql" / "006_catalogue_regression.sql").read_text(
        encoding="utf-8")

    for sql, name in ((pair, "the per-pair query"), (sweep, "the catalogue sweep")):
        general = sql[sql.index("general_flash_qualifying"):sql.index("red_flash_qualifying")]
        red = sql[sql.index("red_flash_qualifying"):]
        assert "luma_min < 0.80" in general, f"{name} lost the darker-image ceiling"
        assert "luma_min" not in red, f"{name} applied a luminance condition to the red rule"


def test_ground_truth_never_reads_a_measurement_column():
    """The evaluation is only a measurement if the two sides are independent.

    If the ground-truth query looked at `luma_delta` or `red_delta`, it would be
    re-deriving the detector's own answer and the confusion matrix would be
    circular. It may read only which assets exist, and recompute the generator's
    planting hashes.
    """
    from pathlib import Path

    sql = (Path(__file__).resolve().parent.parent / "sql" / "008_ground_truth.sql").read_text(
        encoding="utf-8")
    body = sql[sql.index("*/") + 2:]  # the header comment names them to explain the rule

    for measurement in ("luma_delta", "red_delta", "luma_min",
                        "changed_area_fraction", "direction", "pts_ms"):
        assert measurement not in body, (
            f"the ground-truth query reads {measurement}; it must not depend on any measurement"
        )
    assert "sipHash64" in body, "it must recompute the generator's planting decisions"
    assert "toUInt64" in body, (
        "title_index must be cast to UInt64 or sipHash64 hashes a different value "
        "than the generator did, and the comparison silently scores the wrong set"
    )


def test_ground_truth_and_detector_are_different_queries():
    """Guard against someone 'simplifying' the evaluation into a tautology."""
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent / "sql"
    truth = root.joinpath("008_ground_truth.sql").read_text(encoding="utf-8")
    detector = root.joinpath("006_catalogue_regression.sql").read_text(encoding="utf-8")

    assert "win_transitions" not in truth, "the ground truth must not evaluate the criteria"
    assert "sipHash64" not in detector, "the detector must not know where anything was planted"
