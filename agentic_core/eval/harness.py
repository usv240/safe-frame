"""Reproducible evaluation with a frozen-commit check and durable taint ledger."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Callable, Literal, Mapping, Protocol, Sequence

Outcome = Literal["correct", "abstained", "false_confident", "missed"]


class FreezeVerifier(Protocol):
    def verify(self, frozen_commit: str) -> None: ...


class GitFreezeVerifier:
    """Require the declared commit to be HEAD and to carry an eval-freeze tag."""

    def __init__(self, repo_dir: Path) -> None:
        self.repo_dir = repo_dir

    def _git(self, *args: str) -> str:
        completed = subprocess.run(
            ["git", *args], cwd=self.repo_dir, check=True, capture_output=True, text=True
        )
        return completed.stdout.strip()

    def verify(self, frozen_commit: str) -> None:
        head = self._git("rev-parse", "HEAD")
        declared = self._git("rev-parse", frozen_commit)
        if head != declared:
            raise RuntimeError("held-out evaluation requires frozen_commit to equal HEAD")
        tags = self._git("tag", "--points-at", head).splitlines()
        if not any(tag.startswith("eval-freeze-") for tag in tags):
            raise RuntimeError("held-out evaluation requires an eval-freeze-* tag at HEAD")


@dataclass(frozen=True, slots=True)
class EvalItemResult:
    item_id: str
    outcome: Outcome
    latency_ms: int
    citation_decisive: int = 0
    citation_supported: int = 0
    partner_cost_usd: float = 0.0
    decisive_sources: tuple[str, ...] = ()
    failure_note: str | None = None


@dataclass(frozen=True, slots=True)
class EvalReport:
    split: str
    frozen_commit: str
    corpus_sha256: Mapping[str, str]
    results: tuple[EvalItemResult, ...]

    def counts(self) -> dict[str, int]:
        names: tuple[Outcome, ...] = ("correct", "abstained", "false_confident", "missed")
        return {name: sum(item.outcome == name for item in self.results) for name in names}

    def to_dict(self) -> dict[str, object]:
        latencies = sorted(item.latency_ms for item in self.results)
        decisive = sum(item.citation_decisive for item in self.results)
        supported = sum(item.citation_supported for item in self.results)
        return {
            "split": self.split,
            "frozen_commit": self.frozen_commit,
            "corpus_sha256": dict(self.corpus_sha256),
            "counts": self.counts(),
            "citation_precision": supported / decisive if decisive else None,
            "p50_latency_ms": _percentile(latencies, 0.50),
            "p95_latency_ms": _percentile(latencies, 0.95),
            "cost_per_item_usd": (
                sum(item.partner_cost_usd for item in self.results) / len(self.results)
                if self.results
                else 0.0
            ),
            "coverage": sorted({source for item in self.results for source in item.decisive_sources}),
            "results": [asdict(item) for item in self.results],
        }


def _percentile(values: Sequence[int], fraction: float) -> int | None:
    if not values:
        return None
    return values[round((len(values) - 1) * fraction)]


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class TaintLedger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _load(self) -> dict[str, dict[str, str]]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def claim_once(self, *, split: str, frozen_commit: str, item_id: str) -> None:
        if split != "held-out":
            return
        ledger = self._load()
        key = f"{frozen_commit}:{split}:{item_id}"
        if key in ledger:
            raise RuntimeError(f"TAINTED: held-out item {item_id!r} was already attempted")
        ledger[key] = {"commit": frozen_commit, "split": split, "item_id": item_id}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(ledger, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)


SystemRunner = Callable[[Path, Mapping[str, object]], EvalItemResult]


def run_eval(
    system: SystemRunner,
    corpus_dir: Path,
    answer_key: Mapping[str, Mapping[str, object]],
    *,
    split: str,
    frozen_commit: str,
    verifier: FreezeVerifier,
    ledger_path: Path,
) -> EvalReport:
    """Run each item once; held-out claims are recorded before system execution."""

    if split == "held-out":
        verifier.verify(frozen_commit)
    files = sorted(path for path in corpus_dir.iterdir() if path.is_file())
    file_by_id = {path.stem: path for path in files}
    expected_ids = sorted(
        item_id for item_id, expected in answer_key.items() if expected.get("split") == split
    )
    missing = [item_id for item_id in expected_ids if item_id not in file_by_id]
    if missing:
        raise FileNotFoundError(f"corpus is missing answer-key items: {missing}")

    ledger = TaintLedger(ledger_path)
    results: list[EvalItemResult] = []
    hashes: dict[str, str] = {}
    for item_id in expected_ids:
        path = file_by_id[item_id]
        hashes[path.name] = _sha256(path)
        ledger.claim_once(split=split, frozen_commit=frozen_commit, item_id=item_id)
        started = time.perf_counter()
        result = system(path, answer_key[item_id])
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        if result.item_id != item_id:
            raise ValueError(f"system returned {result.item_id!r} for {item_id!r}")
        if result.latency_ms < 0:
            result = EvalItemResult(**{**asdict(result), "latency_ms": elapsed_ms})
        results.append(result)

    return EvalReport(
        split=split,
        frozen_commit=frozen_commit,
        corpus_sha256=hashes,
        results=tuple(results),
    )

