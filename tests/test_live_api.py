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


def test_landing_page_has_no_flashing_media_and_exposes_judge_proof():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert "Run real ClickHouse proof" in response.text
    assert "This page contains no flashing media" in response.text
    assert "<video" not in response.text
    assert "prefers-color-scheme" not in response.text
    assert "Dark" in response.text


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
    assert body["gate"]["failed"] == ["no_child_only_general_flash"]


def test_scan_rejects_cross_lineage_comparison():
    parent = burst("master", "master", 6)
    child = burst("child", "60fps", 7)
    child[0]["lineage_id"] = "different-tree"
    response = TestClient(app).post("/v1/scan", json={"parent_metrics": parent, "rendition_metrics": child})
    assert response.status_code == 422
