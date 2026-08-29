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
