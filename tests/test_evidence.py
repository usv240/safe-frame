from datetime import UTC, datetime

import pytest

from agentic_core.evidence import Claim, Source, stable_claim_id


def test_verified_source_makes_claim_gate_eligible() -> None:
    source = Source(
        url="https://archive.example.org/item/42",
        domain="archive.example.org",
        excerpt="The catalogue identifies the actor and release year.",
        retrieved_at=datetime(2026, 8, 20, tzinfo=UTC),
        verified=True,
    )
    claim = Claim(
        claim_id=stable_claim_id("fragment-1", "has-candidate", "film-42"),
        claim_text="Fragment 1 may be from Film 42.",
        subject="fragment-1",
        agent_id="phrase-hunter",
        stance="supports",
        sources=(source,),
        confidence_basis="A verified catalogue excerpt contains the rare intertitle phrase.",
    )

    assert claim.is_decisive_eligible
    assert claim.independent_domains == {"archive.example.org"}


def test_source_rejects_hostname_mismatch() -> None:
    with pytest.raises(ValueError, match="domain"):
        Source(
            url="https://archive.example.org/item/42",
            domain="other.example.org",
            excerpt="Supporting text.",
        )


def test_unsourced_claim_cannot_contribute_to_gate() -> None:
    claim = Claim(
        claim_id=stable_claim_id("fragment-1", "looks-like", "1917"),
        claim_text="The costume appears consistent with 1917.",
        subject="fragment-1",
        agent_id="visual-examiner",
        stance="neutral",
        confidence_basis="Visual estimate only; no external evidence has been verified.",
    )

    assert not claim.is_decisive_eligible

