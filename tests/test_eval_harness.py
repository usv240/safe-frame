from pathlib import Path

import pytest

from agentic_core.eval import EvalItemResult, run_eval


class Frozen:
    def verify(self, frozen_commit: str) -> None:
        assert frozen_commit == "abc123"


def test_held_out_item_cannot_be_rerun(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "fragment-01.bin").write_bytes(b"original material")
    answer_key = {"fragment-01": {"split": "held-out", "expected": "abstain"}}

    def system(path: Path, expected: object) -> EvalItemResult:
        return EvalItemResult(item_id=path.stem, outcome="abstained", latency_ms=1)

    kwargs = {
        "split": "held-out",
        "frozen_commit": "abc123",
        "verifier": Frozen(),
        "ledger_path": tmp_path / "ledger.json",
    }
    report = run_eval(system, corpus, answer_key, **kwargs)
    assert report.counts()["abstained"] == 1
    with pytest.raises(RuntimeError, match="TAINTED"):
        run_eval(system, corpus, answer_key, **kwargs)


def test_report_includes_hashes_failures_and_latency(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "fragment-01.bin").write_bytes(b"dev material")
    answer_key = {"fragment-01": {"split": "dev", "expected": "identify"}}
    report = run_eval(
        lambda path, expected: EvalItemResult(
            item_id=path.stem,
            outcome="false_confident",
            latency_ms=25,
            citation_decisive=2,
            citation_supported=1,
            partner_cost_usd=0.02,
            failure_note="Competing attribution was not disproved.",
        ),
        corpus,
        answer_key,
        split="dev",
        frozen_commit="working-tree",
        verifier=Frozen(),
        ledger_path=tmp_path / "ledger.json",
    ).to_dict()
    assert report["counts"]["false_confident"] == 1
    assert report["citation_precision"] == 0.5
    assert report["p95_latency_ms"] == 25
    assert len(report["corpus_sha256"]["fragment-01.bin"]) == 64

