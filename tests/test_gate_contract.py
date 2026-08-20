import pytest

from agentic_core.gate import Candidate, GateResult


def test_gate_exposes_passed_and_failed_thresholds() -> None:
    result = GateResult(
        verdict="abstain",
        reason="Only two independent domains were verified.",
        thresholds={
            "independent_domains>=3": False,
            "distinct_clue_families>=2": True,
        },
        requires_human=True,
    )

    assert result.passed == ("distinct_clue_families>=2",)
    assert result.failed == ("independent_domains>=3",)


def test_candidate_score_is_bounded() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        Candidate(candidate_id="candidate-1", label="Example", score=1.01)

