"""Keys must raise limits without ever becoming a gate.

The submission has to be testable without an account, so the single most
important property here is the boring one: with no credential at all, every
endpoint behaves exactly as it did before keys existed. The rest of these tests
are the edge cases a caller will actually hit, because a key system that fails
vaguely is worse than none.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from safe_frame import apikeys
from safe_frame.apikeys import (
    ANONYMOUS_TIER,
    KEYED_TIER,
    MAX_AGE_DAYS,
    ApiKeyError,
    identify,
    mint,
    verify,
)
from safe_frame.main import app


SECRET = "test-signing-secret-not-a-real-one"


@pytest.fixture(name="secret")
def _secret(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("SAFE_FRAME_API_KEY_SECRET", SECRET)
    return SECRET


@pytest.fixture(name="client")
def _client() -> TestClient:
    return TestClient(app)


def test_a_minted_key_verifies(secret: str) -> None:
    issued = mint()
    identity = verify(str(issued["api_key"]))
    assert identity.tier == KEYED_TIER
    assert identity.key_id == issued["key_id"]


def test_no_credential_is_anonymous_not_an_error(secret: str) -> None:
    assert identify(None, None).tier == ANONYMOUS_TIER


def test_anonymous_access_still_works_when_keys_are_unavailable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The judge path must not depend on the key system being configured."""
    monkeypatch.delenv("SAFE_FRAME_API_KEY_SECRET", raising=False)
    assert client.get("/health").status_code == 200
    assert client.get("/v1/samples").status_code == 200
    body = client.get("/v1/keys/self").json()["data"]
    assert body["tier"] == ANONYMOUS_TIER
    assert body["keys_available"] is False


def test_minting_is_refused_clearly_when_unconfigured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SAFE_FRAME_API_KEY_SECRET", raising=False)
    response = client.post("/v1/keys")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "api_keys_unavailable"


def test_mint_and_describe_round_trip(client: TestClient, secret: str) -> None:
    key = client.post("/v1/keys").json()["data"]["api_key"]
    for header in ({"Authorization": f"Bearer {key}"}, {"X-API-Key": key}):
        body = client.get("/v1/keys/self", headers=header).json()["data"]
        assert body["tier"] == KEYED_TIER
        assert body["quota_multiplier"] > 1


@pytest.mark.parametrize(
    "token,fragment",
    [
        ("", "malformed"),
        ("nonsense", "malformed"),
        ("sf_abc", "malformed"),
        ("xx_abc_123_def", "malformed"),
        ("sf__123_def", "malformed"),
        ("sf_abc_notanumber_def", "not a number"),
        ("sf_abc_0_def", "not in the past"),
    ],
)
def test_malformed_keys_are_refused_with_a_reason(
    secret: str, token: str, fragment: str
) -> None:
    with pytest.raises(ApiKeyError, match=fragment):
        verify(token)


def test_a_forged_signature_is_refused(secret: str) -> None:
    key = str(mint()["api_key"])
    forged = key[:-1] + ("0" if key[-1] != "0" else "1")
    with pytest.raises(ApiKeyError, match="signature"):
        verify(forged)


def test_a_key_signed_with_another_secret_is_refused(
    monkeypatch: pytest.MonkeyPatch, secret: str
) -> None:
    key = str(mint()["api_key"])
    monkeypatch.setenv("SAFE_FRAME_API_KEY_SECRET", "a-completely-different-secret")
    with pytest.raises(ApiKeyError, match="signature"):
        verify(key)


def test_an_expired_key_is_refused(secret: str, monkeypatch: pytest.MonkeyPatch) -> None:
    key = str(mint()["api_key"])
    real = time.time
    monkeypatch.setattr(
        apikeys.time, "time", lambda: real() + (MAX_AGE_DAYS + 2) * 86_400
    )
    with pytest.raises(ApiKeyError, match="expire"):
        verify(key)


def test_a_non_bearer_authorization_header_is_refused(secret: str) -> None:
    with pytest.raises(ApiKeyError, match="Bearer"):
        identify("Basic dXNlcjpwYXNz", None)


def test_a_broken_key_is_refused_rather_than_downgraded(
    client: TestClient, secret: str
) -> None:
    """Silently treating a bad key as anonymous would hide the caller's mistake."""
    response = client.post(
        "/v1/triage",
        json={"operator_id": "edge-case"},
        headers={"X-API-Key": "sf_dead_1_beef"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_api_key"
    assert "hint" in response.json()["detail"]


def test_the_key_states_that_it_cannot_be_revoked(secret: str) -> None:
    """An honest limitation belongs on the credential, not only in the docs."""
    assert "cannot be revoked" in str(mint()["note"])
