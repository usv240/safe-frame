"""Bring-your-own-clip analysis must behave exactly like the catalogue path.

The catalogue demonstrates the product on content we chose, which is a fair
thing for a judge to discount. `/v1/analyze` lets anyone put their own clip
through the same measurement stage and the same rules, so these tests hold it
to the same claims the catalogue makes:

* a clip that does not flash passes,
* a clip that flashes in luminance is caught,
* a clip that alternates saturated red at *matched luminance* is caught by the
  red rule and not the luminance one, which is the whole argument for
  implementing both, and
* a rendition whose master carries the same burst is **not** a regression,
  which is the difference between this product and a flash detector.

The frames are constructed here rather than decoded from a file: no video is
committed, and nothing in the suite renders anything.
"""

from __future__ import annotations

import base64

import numpy as np
import pytest
from fastapi.testclient import TestClient

from safe_frame.analyze import FrameDecodeError, measure_clip, per_second_counts
from safe_frame.detector import detect_violations
from safe_frame.main import app


WIDTH = HEIGHT = 16
FRAMES = 60
RATE = 25.0

# A grey whose relative luminance matches saturated red, so an alternation
# between them holds luminance nearly flat while the red difference swings.
LUMA_MATCHED_GREY = (124, 124, 124)
SATURATED_RED = (255, 0, 0)


def _clip(*, flashing: bool = False, red: bool = False) -> dict[str, object]:
    frames = []
    for index in range(FRAMES):
        frame = np.full((HEIGHT, WIDTH, 3), 60, np.uint8)
        if flashing and 10 <= index < 40:
            if red:
                frame[:, :] = SATURATED_RED if index % 2 == 0 else LUMA_MATCHED_GREY
            else:
                frame[:, :] = (250, 250, 250) if index % 2 == 0 else (20, 20, 20)
        frames.append(frame)
    return {
        "frames_b64": base64.b64encode(np.stack(frames).tobytes()).decode(),
        "width": WIDTH,
        "height": HEIGHT,
        "frame_count": FRAMES,
        "frame_rate": RATE,
    }


@pytest.fixture(name="client")
def _client() -> TestClient:
    return TestClient(app)


def _analyze(client: TestClient, body: dict[str, object]) -> dict[str, object]:
    response = client.post("/v1/analyze", json=body)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_a_clip_that_does_not_flash_passes(client: TestClient) -> None:
    data = _analyze(client, {"rendition": _clip()})
    assert data["mode"] == "absolute"
    assert data["verdict"] == "pass"
    assert data["findings"] == []


def test_a_luminance_flash_is_caught(client: TestClient) -> None:
    data = _analyze(client, {"rendition": _clip(flashing=True)})
    assert data["verdict"] == "fail"
    assert [item["rule"] for item in data["findings"]] == ["general_flash"]


def test_red_alternation_at_matched_luminance_is_caught_only_by_the_red_rule(
    client: TestClient,
) -> None:
    """The blind spot the product exists to close, on a caller's own frames."""
    data = _analyze(client, {"rendition": _clip(flashing=True, red=True)})
    assert data["verdict"] == "fail"
    assert [item["rule"] for item in data["findings"]] == ["red_flash"]


def test_a_rendition_that_introduces_a_flash_is_a_regression(client: TestClient) -> None:
    data = _analyze(client, {"rendition": _clip(flashing=True), "master": _clip()})
    assert data["mode"] == "regression"
    assert data["verdict"] == "fail"
    assert [item["rule"] for item in data["findings"]] == ["general_flash"]
    assert data["master"] is not None


def test_a_flash_inherited_from_the_master_is_not_a_regression(client: TestClient) -> None:
    """Both sides flash identically, so the conversion introduced nothing.

    This is the decoy case. A plain flash detector fails this clip; Safe Frame
    must pass it, or the product is only a flash detector with extra steps.
    """
    data = _analyze(
        client, {"rendition": _clip(flashing=True), "master": _clip(flashing=True)}
    )
    assert data["mode"] == "regression"
    assert data["verdict"] == "pass"
    assert data["findings"] == []
    # the rendition really does violate on its own terms
    assert data["rendition"]["violations"], "the fixture stopped exercising the decoy"


def test_findings_have_one_shape_in_both_modes(client: TestClient) -> None:
    absolute = _analyze(client, {"rendition": _clip(flashing=True)})
    regression = _analyze(
        client, {"rendition": _clip(flashing=True), "master": _clip()}
    )
    assert set(absolute["findings"][0]) == set(regression["findings"][0])


def test_the_result_never_claims_certification(client: TestClient) -> None:
    data = _analyze(client, {"rendition": _clip(flashing=True)})
    assert data["certified"] is False
    assert data["requires_human"] is True
    assert "grid" in data["measurement"] and data["measurement"]["note"]


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ({"frame_count": 9_999}, 422),
        ({"width": 9_999}, 422),
        ({"frame_rate": 0}, 422),
        ({"frames_b64": "not!valid!base64"}, 400),
    ],
)
def test_malformed_submissions_are_refused(
    client: TestClient, mutation: dict[str, object], expected: int
) -> None:
    clip = _clip()
    clip.update(mutation)
    assert client.post("/v1/analyze", json={"rendition": clip}).status_code == expected


def test_a_truncated_buffer_is_refused_rather_than_measured_short() -> None:
    """A short upload must fail loudly, not be measured as a shorter clip."""
    clip = _clip()
    raw = base64.b64decode(clip["frames_b64"])
    with pytest.raises(FrameDecodeError, match="bytes"):
        measure_clip(
            base64.b64encode(raw[: len(raw) // 2]).decode(),
            width=WIDTH,
            height=HEIGHT,
            frame_count=FRAMES,
            frame_rate=RATE,
            asset_id="truncated",
            lineage_id="L",
        )


def test_per_second_counts_track_the_burst() -> None:
    clip = _clip(flashing=True)
    metrics = measure_clip(
        clip["frames_b64"],
        width=WIDTH,
        height=HEIGHT,
        frame_count=FRAMES,
        frame_rate=RATE,
        asset_id="burst",
        lineage_id="L",
    )
    counts = per_second_counts(metrics)
    assert counts, "the chart series must not be empty for a flashing clip"
    assert max(item["general_flash"] for item in counts) > 6
    assert detect_violations(metrics), "fixture no longer violates"


def test_analysing_a_submission_never_writes_to_the_database(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The privacy claim on every result is that nothing is stored. Enforce it.

    This path used to persist the submitted pair and then run the stored
    anti-join, which kept measurements derived from somebody's own video in the
    database indefinitely.

    The ClickHouse branch has to be forced on. Without credentials the handler
    never enters it, so a first version of this test passed happily while a
    re-introduced write sat in the very branch it was meant to guard.
    """
    from safe_frame import main as main_module

    async def refuse(*args: object, **kwargs: object) -> object:
        raise AssertionError("/v1/analyze must not persist anything a visitor submitted")

    def refuse_sync(*args: object, **kwargs: object) -> int:
        raise AssertionError("/v1/analyze must not persist anything a visitor submitted")

    async def no_findings(*args: object, **kwargs: object) -> list[object]:
        return []

    monkeypatch.setattr(main_module, "_configured", lambda *names: True)
    monkeypatch.setattr(main_module, "persist_violations", refuse_sync)
    monkeypatch.setattr(main_module, "regression_count", refuse)
    monkeypatch.setattr(main_module, "parity_violations", no_findings)
    monkeypatch.setattr(main_module, "submitted_regressions", no_findings)

    for body in (
        {"rendition": _clip(flashing=True)},
        {"rendition": _clip(flashing=True), "master": _clip()},
    ):
        response = client.post("/v1/analyze", json=body)
        assert response.status_code == 200, response.text
        assert response.json()["data"]["decision_source"] == "clickhouse_sql_via_official_mcp"


def test_the_result_states_what_is_stored(client: TestClient) -> None:
    data = _analyze(client, {"rendition": _clip()})
    privacy = data["privacy"]
    assert privacy["what_is_stored"].startswith("nothing")
    for key in ("file_never_uploaded", "never_displayed", "what_is_sent", "logs"):
        assert privacy[key]


@pytest.mark.parametrize(
    "name", ["master.webm", "rendition-flash.webm", "rendition-red.webm"]
)
def test_the_sample_clips_are_served(client: TestClient, name: str) -> None:
    """A judge with no video to hand still needs to be able to run the real check."""
    response = client.get(f"/samples/{name}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "video/webm"
    assert len(response.content) > 1000


@pytest.mark.parametrize(
    "name", ["index.html", "../index.html", "..%2findex.html", "evil.webm", "master.WEBM"]
)
def test_only_the_named_sample_clips_are_reachable(client: TestClient, name: str) -> None:
    """Whitelist, not a directory mount: nothing else under web/ is fetchable."""
    assert client.get(f"/samples/{name}").status_code in (404, 400)
