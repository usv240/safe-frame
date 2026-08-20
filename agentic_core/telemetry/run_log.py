"""Small structured telemetry model shared by HTTP responses and persisted traces."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import Any


@dataclass(frozen=True, slots=True)
class TraceEvent:
    kind: str
    name: str
    latency_ms: int
    agent_id: str | None = None
    tokens: int | None = None
    cost_usd: float | None = None
    detail: dict[str, Any] = field(default_factory=dict)


class RunLog:
    def __init__(self, request_id: str) -> None:
        self.request_id = request_id
        self.started_at = datetime.now(UTC)
        self._started_clock = perf_counter()
        self.events: list[TraceEvent] = []

    def add(self, event: TraceEvent) -> None:
        self.events.append(event)

    @property
    def latency_ms(self) -> int:
        return round((perf_counter() - self._started_clock) * 1000)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "started_at": self.started_at.isoformat(),
            "latency_ms": self.latency_ms,
            "events": [asdict(event) for event in self.events],
            "tokens": sum(event.tokens or 0 for event in self.events),
            "cost_usd": round(sum(event.cost_usd or 0 for event in self.events), 6),
        }

