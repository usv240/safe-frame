from safe_frame.detector import detect_general_flashes
from safe_frame.lineage import regressions
from safe_frame.models import TransitionMetric


def burst(asset: str, transform: str, count: int, area: float = 1.0):
    return [
        TransitionMetric(
            asset_id=asset,
            lineage_id="tree-1",
            parent_id="master" if asset != "master" else "",
            transform=transform,
            pts_ms=index * 100,
            luma_delta=0.8,
            red_delta=0,
            changed_area_fraction=area,
            direction="up" if index % 2 == 0 else "down",
        )
        for index in range(count)
    ]


def test_more_than_six_opposing_transitions_fails():
    assert detect_general_flashes(burst("child", "60fps", 7))


def test_six_transitions_passes_boundary():
    assert detect_general_flashes(burst("child", "60fps", 6)) == []


def test_small_area_passes():
    assert detect_general_flashes(burst("child", "crop", 8, area=0.1)) == []


def test_child_only_violation_is_attributed():
    child = detect_general_flashes(burst("child", "60fps", 8))
    result = regressions([], child)
    assert len(result) == 1
    assert result[0].attribution == "60fps"


def test_matching_parent_violation_is_not_regression():
    parent = detect_general_flashes(burst("master", "master", 8))
    child = detect_general_flashes(burst("child", "hdr10", 8))
    assert regressions(parent, child) == []
