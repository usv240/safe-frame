from fastapi.testclient import TestClient

from safe_frame.main import app


def burst(asset: str, transform: str, count: int):
    return [
        {
            "asset_id": asset,
            "lineage_id": "judge-tree",
            "parent_id": "master" if asset != "master" else "",
            "transform": transform,
            "pts_ms": index * 100,
            "luma_delta": 0.8,
            "red_delta": 0,
            "changed_area_fraction": 1.0,
            "direction": "up" if index % 2 == 0 else "down",
        }
        for index in range(count)
    ]


def test_landing_page_is_safe_for_the_audience_it_is_about():
    """A product about photosensitivity does not get to be careless on its own page.

    The page must contain no moving or flashing media, must state that, and must
    disable its own transitions under `prefers-reduced-motion`. It also honours
    the visitor's OS colour preference rather than forcing a bright page on
    someone who chose dark: an unrequested full-screen flash to light is exactly
    the class of thing this product exists to catch. An explicit choice still
    overrides the OS in both directions.
    """
    page = TestClient(app).get("/")
    assert page.status_code == 200
    text = page.text

    assert "<video" not in text and "<canvas" not in text
    assert "no flashing media on this page" in text
    assert "prefers-reduced-motion" in text, "motion must be suppressed for reduced-motion users"
    assert "@keyframes" not in text, "nothing on this page may animate on a loop"

    # three-state theming: OS default, plus an explicit override that wins both ways
    assert "prefers-color-scheme:dark" in text
    assert ':root:not([data-theme="light"])' in text
    assert ':root[data-theme="dark"]' in text


def test_landing_page_exposes_the_judge_path_without_baking_in_the_answer():
    text = TestClient(app).get("/").text
    assert "Sweep the catalogue" in text
    assert "No sweep has been run in this browser session." in text
    assert "certified: false" in text
    # the corpus counters and every result must be fetched, never hard-coded
    for endpoint in ("/v1/catalogue/sweep", "/v1/catalogue/shape",
                     "/v1/catalogue/timeline", "/v1/explain"):
        assert endpoint in text


def test_landing_page_states_where_every_threshold_came_from():
    """Each implemented threshold is traceable, and the unimplemented rule is named."""
    text = TestClient(app).get("/").text
    assert "WCAG 2.3.1" in text
    for threshold in ("0.10", "0.20", "0.25"):
        assert threshold in text
    assert "Spatial pattern" in text and "not implemented" in text
    # the impact claims must carry their sources rather than stand alone
    assert "epi.17175" in text, "prevalence claim must cite the Epilepsy Foundation review"
    assert "ofcom.org.uk" in text and "w3.org" in text


def test_local_scan_is_honest_when_live_catalogue_is_not_configured(monkeypatch):
    monkeypatch.delenv("MCP_CLICKHOUSE_COMMAND", raising=False)
    response = TestClient(app).post(
        "/v1/scan",
        json={"parent_metrics": burst("master", "master", 6), "rendition_metrics": burst("child", "60fps", 7)},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "fail"
    assert body["certified"] is False
    assert body["decision_source"] == "local_reference_precheck"
    assert body["gate"]["failed"] == ["no_child_only_flash_violation"]
    assert body["rules_evaluated"] == ["general_flash", "red_flash"]
    assert [item["rule"] for item in body["rendition_violations"]] == ["general_flash"]


def test_scan_reports_a_red_flash_the_luminance_rule_cannot_see(monkeypatch):
    """A red alternation under the general-flash floor must still fail the scan."""
    monkeypatch.delenv("MCP_CLICKHOUSE_COMMAND", raising=False)
    def red(asset: str, transform: str, count: int):
        rows = burst(asset, transform, count)
        for row in rows:
            row["luma_delta"] = 0.04   # below the 0.10 general-flash floor
            row["red_delta"] = 0.55
        return rows

    response = TestClient(app).post(
        "/v1/scan",
        json={"parent_metrics": red("master", "master", 6), "rendition_metrics": red("child", "social_crop_v", 8)},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "fail"
    assert [item["rule"] for item in body["rendition_violations"]] == ["red_flash"]
    assert [item["child"]["rule"] for item in body["regressions"]] == ["red_flash"]
    assert body["regressions"][0]["attribution"] == "social_crop_v"


def test_scan_rejects_cross_lineage_comparison():
    parent = burst("master", "master", 6)
    child = burst("child", "60fps", 7)
    child[0]["lineage_id"] = "different-tree"
    response = TestClient(app).post("/v1/scan", json={"parent_metrics": parent, "rendition_metrics": child})
    assert response.status_code == 422


def test_landing_page_carries_the_whole_case_without_leaving_the_site():
    """A judge who only opens the URL must find every criterion answered there."""
    text = TestClient(app).get("/").text

    # who it is for, which the brief asks submissions to name
    assert "Who this is for" in text and "distribution QC" in text

    # the partner integration, checkable from the page rather than the README
    assert "/v1/integrations/clickhouse/evidence" in text
    assert "mcp-clickhouse" in text and "read-only" in text
    assert "CLICKHOUSE_ALLOW_WRITE_ACCESS=false" in text, "the credential boundary must be shown"

    # the systemic finding and the multi-step agent
    assert "/v1/catalogue/transform-risk" in text
    assert "/v1/triage" in text
    # read the source rather than import it: this assertion is about the agent's
    # shape, and should not need the ADK runtime installed to run
    from pathlib import Path as _P
    agent_source = (_P(__file__).resolve().parent.parent / "safe_frame" / "adk_app.py").read_text(
        encoding="utf-8")
    for tool in ("survey_regressions", "profile_transform_risk",
                 "count_luminance_blind_spot", "inspect_pair_timeline"):
        assert f"async def {tool}" in agent_source, f"{tool} must be a real agent tool"


def test_triage_request_validates_its_operator():
    response = TestClient(app).post("/v1/triage", json={"operator_id": "x"})
    assert response.status_code == 422


def test_scan_refuses_to_write_over_the_published_catalogue():
    """`/v1/scan` persists what it is given, and the anti-join reads the same table.

    Without this, an anonymous caller could write a violation onto an approved
    master in the published corpus and suppress a real child-only finding,
    turning a documented `fail` into a `pass` on a public URL.
    """
    for reserved in ("approved-master", "title_0022__master", "title_0001__60fps_interp"):
        parent = burst("master-of-mine", "master", 6)
        child = burst(reserved, "60fps", 7)
        for row in parent + child:
            row["lineage_id"] = "attacker-tree"
        response = TestClient(app).post(
            "/v1/scan", json={"parent_metrics": parent, "rendition_metrics": child})
        assert response.status_code == 422, f"{reserved} was accepted as a write target"
        assert "reserved" in response.text


def test_samples_are_isolated_per_request():
    """Two callers must not be able to collide, so identifiers cannot be fixed."""
    client = TestClient(app)
    first = client.get("/v1/samples").json()["data"]
    second = client.get("/v1/samples").json()["data"]
    assert first["parent_metrics"][0]["asset_id"] != second["parent_metrics"][0]["asset_id"]
    assert first["parent_metrics"][0]["lineage_id"] != second["parent_metrics"][0]["lineage_id"]
    # and what /v1/samples hands out must be something /v1/scan will accept
    response = client.post("/v1/scan", json={
        "parent_metrics": first["parent_metrics"],
        "rendition_metrics": first["rendition_metrics"]})
    assert response.status_code == 200, response.text
    assert response.json()["verdict"] == "fail"


def test_expensive_endpoints_are_capped_and_reads_are_not(monkeypatch):
    """Model-spending endpoints are limited; every read stays open for judging."""
    import safe_frame.main as main

    monkeypatch.setattr(main, "_CALLS", {})
    client = TestClient(app)
    # /v1/scan is the write path and is capped at 20/min
    payload = client.get("/v1/samples").json()["data"]
    body = {"parent_metrics": payload["parent_metrics"],
            "rendition_metrics": payload["rendition_metrics"]}
    codes = {client.post("/v1/scan", json=body).status_code for _ in range(25)}
    assert 429 in codes, "an unbounded loop against the write path was not capped"

    # the agent endpoints are capped harder, and an import or runtime failure
    # there must still fail closed rather than surface a stack trace
    monkeypatch.setattr(main, "_CALLS", {})
    agent_codes = {client.post("/v1/triage", json={"operator_id": "loop"}).status_code
                   for _ in range(10)}
    assert 429 in agent_codes, "an unbounded loop against the agent was not capped"
    assert agent_codes <= {429, 502}, f"the agent leaked an unexpected status: {agent_codes}"

    # reads must never be rate limited: judging requires testing without a quota
    monkeypatch.setattr(main, "_CALLS", {})
    assert all(client.get("/v1/samples").status_code == 200 for _ in range(40))
    assert client.get("/health").status_code == 200


def test_run_logs_are_cloud_logging_shaped_and_carry_no_payload(capsys):
    """An agent that reads a database is only trustworthy if its runs are reconstructable.

    Cloud Run lifts `severity` and `message` out of JSON on stdout and puts the
    rest in `jsonPayload`, so the shape is what makes these queryable. The tool
    sequence is the audit trail; the submitted metrics and the model's prose are
    deliberately not logged.
    """
    import json as _json

    from safe_frame.telemetry import log_event

    log_event("agent_run", agent="QcTriageAgent", tools_called=["survey_regressions"],
              steps=1, elapsed_ms=12.3, decision_source="clickhouse_sql")
    entry = _json.loads(capsys.readouterr().out.strip().splitlines()[-1])

    assert entry["severity"] == "INFO"
    assert entry["message"] == "agent_run"
    assert entry["event"] == "agent_run"
    assert entry["tools_called"] == ["survey_regressions"]
    assert entry["decision_source"] == "clickhouse_sql"


def test_telemetry_never_breaks_a_request():
    """A logging failure must not take down the endpoint it is describing."""
    from safe_frame.telemetry import log_event

    class Unserialisable:
        def __repr__(self):
            raise RuntimeError("boom")

    log_event("agent_run", payload=Unserialisable())  # must not raise


def test_the_page_shows_the_criteria_that_actually_run():
    """The landing page prints the criteria as evidence, so it must not drift.

    The SQL panel omitted the darker-image condition after that condition was
    added, which put the page in contradiction with its own criteria table two
    sections above it. A judge reading both would find the page arguing with
    itself.
    """
    from pathlib import Path as _P
    import inspect

    from safe_frame.detector import detect_general_flashes

    text = TestClient(app).get("/").text
    sweep = (_P(__file__).resolve().parent.parent / "sql" / "006_catalogue_regression.sql").read_text(
        encoding="utf-8")
    defaults = inspect.signature(detect_general_flashes).parameters

    # every threshold the sweep applies must be visible on the page
    for shown in (f"{defaults['luma_delta_floor'].default:.2f}",
                  f"{defaults['darker_image_ceiling'].default:.2f}",
                  f"{defaults['area_floor'].default:.2f}",
                  str(defaults['max_transitions_per_second'].default)):
        assert shown in text, f"the page does not show {shown}"

    # Scope this to the SQL panel itself. Asserting the string appears anywhere
    # on the page passed while the panel was stale, because the criteria table
    # two sections above already carried it -- a false pass that let the page
    # ship contradicting itself.
    import re as _re

    panel = _re.search(r'<div class="sqlbox".*?</div>', text, _re.S)
    assert panel, "the SQL panel is gone from the page"
    panel_text = panel.group(0)
    for condition in ("luma_delta &gt;= 0.10", "luma_min &lt; 0.80",
                      "changed_area_fraction &gt;= 0.25", "win_transitions &gt; 6"):
        assert condition in panel_text, f"the SQL panel does not show {condition}"
    assert "luma_min < 0.80" in sweep, "the sweep lost the darker-image condition"


def test_live_answers_are_never_cacheable() -> None:
    """This page claims every panel is computed on the press. That claim used to
    depend on no browser or proxy choosing to cache a GET, because the answers
    carried no cache directive at all. A deterministic query over a fixed corpus
    returns the same numbers every time, so a cached response is indistinguishable
    from a fresh one by looking at it, which is exactly why the header has to say so.
    """
    client = TestClient(app)
    for path in ("/health", "/v1/stack", "/v1/catalogue/shape"):
        response = client.get(path)
        assert response.headers.get("cache-control") == "no-store", (
            f"{path} may be cached, which would let a stale answer look live"
        )
