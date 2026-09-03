"""The agent module must at least import, and keep the shape the product depends on.

Nothing imported `safe_frame.adk_app` anywhere in the suite: `test_live_api.py`
reads it as *text* to inspect its source. So the whole suite once passed 47/47
with an unterminated string literal in it. `compileall` in CI would have caught
the syntax error, but not a bad import, a renamed entry point, or a tool
quietly dropped from the triage agent -- and those are the parts the demo and
the partner-track requirement both rest on.

This costs milliseconds and needs no credentials, because both agents are built
inside their entry points rather than at module scope.
"""

from __future__ import annotations

import inspect

import safe_frame.adk_app as adk_app


def test_agent_module_imports_and_exposes_its_entry_points() -> None:
    for name in ("triage_catalogue", "explain_regression"):
        assert hasattr(adk_app, name), f"adk_app lost its {name} entry point"
        assert inspect.iscoroutinefunction(getattr(adk_app, name))


def test_triage_agent_still_declares_its_four_tools() -> None:
    """The multi-step claim is four tools. Losing one silently would weaken it."""
    source = inspect.getsource(adk_app)
    for tool in (
        "survey_regressions",
        "profile_transform_risk",
        "count_luminance_blind_spot",
        "inspect_pair_timeline",
    ):
        assert source.count(tool) >= 2, f"{tool} is no longer wired into the triage agent"


def test_the_brief_is_constrained_to_plain_punctuation() -> None:
    """The brief renders verbatim in the UI, which is kept free of em dashes."""
    assert "em dash" in inspect.getsource(adk_app)
