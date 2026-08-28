from safe_frame.detector import detect_general_flashes, detect_red_flashes, detect_violations
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


def red_burst(asset: str, transform: str, count: int, *, luma: float = 0.04, red: float = 0.55):
    """A saturated-red alternation whose luminance stays under the general floor."""
    return [
        TransitionMetric(
            asset_id=asset,
            lineage_id="tree-1",
            parent_id="master" if asset != "master" else "",
            transform=transform,
            pts_ms=index * 100,
            luma_delta=luma,
            red_delta=red,
            changed_area_fraction=0.8,
            direction="up" if index % 2 == 0 else "down",
        )
        for index in range(count)
    ]


def test_red_flash_is_caught_where_the_luminance_rule_is_silent():
    """The blind spot a luminance-only detector has, stated as a test."""
    rows = red_burst("child", "social_crop", 8)
    assert detect_general_flashes(rows) == [], "luma is below the general-flash floor"
    found = detect_red_flashes(rows)
    assert len(found) == 1
    assert found[0].rule == "red_flash"


def test_red_flash_respects_the_same_six_per_second_boundary():
    assert detect_red_flashes(red_burst("child", "social_crop", 6)) == []
    assert detect_red_flashes(red_burst("child", "social_crop", 7))


def test_red_flash_needs_saturated_red_not_merely_present_red():
    assert detect_red_flashes(red_burst("child", "social_crop", 9, red=0.19)) == []
    assert detect_red_flashes(red_burst("child", "social_crop", 9, red=0.20))


def test_detect_violations_reports_each_rule_that_fired():
    both = burst("child", "60fps", 8)
    for item in both:
        item.red_delta = 0.9
    assert [item.rule for item in detect_violations(both)] == ["general_flash", "red_flash"]


def test_a_red_regression_is_not_excused_by_a_luminance_flash_in_the_master():
    """The anti-join is keyed on rule, so the master must match rule-for-rule."""
    parent = detect_violations(burst("master", "master", 8))
    child = detect_violations(red_burst("child", "subtitle_burnin", 8))
    introduced = regressions(parent, child)
    assert [item.child.rule for item in introduced] == ["red_flash"]
    assert introduced[0].attribution == "subtitle_burnin"
