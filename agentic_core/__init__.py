"""Shared, evidence-first building blocks vendored into each submission."""

from agentic_core.evidence.models import Claim, Source
from agentic_core.gate.models import Candidate, GateResult, Verdict

__all__ = ["Candidate", "Claim", "GateResult", "Source", "Verdict"]

