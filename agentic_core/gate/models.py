"""Pure deterministic decision-gate contracts. No model calls belong here."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Mapping, Protocol, Sequence

from agentic_core.evidence.models import Claim

Verdict = Literal["confirmed", "probable", "candidates", "abstain", "contradicted"]


@dataclass(frozen=True, slots=True)
class Candidate:
    candidate_id: str
    label: str
    score: float
    decisive_claim_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 1:
            raise ValueError("candidate score must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class GateResult:
    verdict: Verdict
    reason: str
    thresholds: Mapping[str, bool]
    candidates: tuple[Candidate, ...] = ()
    requires_human: bool = False

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("a gate must explain its verdict")
        if not self.thresholds:
            raise ValueError("a gate must expose every evaluated threshold")

    @property
    def passed(self) -> tuple[str, ...]:
        return tuple(name for name, value in self.thresholds.items() if value)

    @property
    def failed(self) -> tuple[str, ...]:
        return tuple(name for name, value in self.thresholds.items() if not value)


class Gate(Protocol):
    def evaluate(
        self,
        claims: Sequence[Claim],
        context: Mapping[str, object],
    ) -> GateResult: ...

