"""Optional API keys: a higher quota for people building against this, never a gate.

The product must stay testable without an account. That is a submission
requirement, and it is also the right default for a safety pre-check: anyone
should be able to run a clip through it without asking permission. So every
endpoint that works anonymously today still works anonymously, at exactly the
limits it had before. A key does one thing: it raises the per-minute cap on the
few endpoints that spend model tokens or write, and names the caller in the
logs so a run can be traced afterwards.

**Keys are stateless.** A key is its own proof: an identifier and an issue date,
signed with an HMAC the server holds. Verification is a signature check, so
there is no table to migrate, no write path on the request, and nothing to lose
when an instance restarts. The trade is that an individual key cannot be revoked
without rotating the signing secret, which is the honest cost of not running a
credential database for a hackathon pre-check, and `REVOCATION_NOTE` says so on
the key itself rather than leaving someone to find out.

Keys expire on their own after `MAX_AGE_DAYS`, which bounds the blast radius of
a leaked key without needing revocation.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass

PREFIX = "sf"
MAX_AGE_DAYS = 90
_SECRET_ENV = "SAFE_FRAME_API_KEY_SECRET"

# Anonymous callers keep the limits the service already had. A key raises them.
ANONYMOUS_TIER = "anonymous"
KEYED_TIER = "keyed"
TIER_MULTIPLIER = {ANONYMOUS_TIER: 1, KEYED_TIER: 5}

REVOCATION_NOTE = (
    "This key is stateless and signed, so it cannot be revoked individually. It stops "
    f"working {MAX_AGE_DAYS} days after issue. Do not embed it in anything you publish; "
    "mint a new one per integration instead."
)


class ApiKeyError(ValueError):
    """A key was supplied and is not usable. Absence of a key is never this."""


@dataclass(frozen=True)
class ApiKeyIdentity:
    """Who is calling, and at what quota."""

    tier: str
    key_id: str | None = None

    @property
    def is_keyed(self) -> bool:
        return self.tier == KEYED_TIER


ANONYMOUS = ApiKeyIdentity(tier=ANONYMOUS_TIER)


def _signing_secret() -> str | None:
    value = os.getenv(_SECRET_ENV)
    return value if value else None


def configured() -> bool:
    """Whether this deployment can mint and verify keys at all."""
    return _signing_secret() is not None


def _sign(key_id: str, issued_at: int, secret: str) -> str:
    payload = f"{key_id}:{issued_at}".encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()[:32]


def mint() -> dict[str, object]:
    """Issue a key. No account, no email, no approval step.

    Returned once and never stored, because there is nowhere to store it: the
    signature is the record.
    """
    secret = _signing_secret()
    if secret is None:
        raise ApiKeyError("this deployment has no signing secret configured, so it cannot issue keys")
    key_id = secrets.token_hex(8)
    issued_at = int(time.time())
    token = f"{PREFIX}_{key_id}_{issued_at}_{_sign(key_id, issued_at, secret)}"
    return {
        "api_key": token,
        "key_id": key_id,
        "issued_at": issued_at,
        "expires_after_days": MAX_AGE_DAYS,
        "quota_multiplier": TIER_MULTIPLIER[KEYED_TIER],
        "send_as": "Authorization: Bearer <api_key>, or X-API-Key: <api_key>",
        "note": REVOCATION_NOTE,
        "anonymous_still_works": (
            "Every endpoint works without a key at the standard limits. A key only raises "
            "the per-minute cap on the endpoints that spend model tokens or write."
        ),
    }


def verify(token: str) -> ApiKeyIdentity:
    """Check a supplied key, or raise ApiKeyError explaining precisely why not."""
    secret = _signing_secret()
    if secret is None:
        raise ApiKeyError("this deployment has no signing secret configured, so it cannot verify keys")

    parts = token.strip().split("_")
    if len(parts) != 4 or parts[0] != PREFIX:
        raise ApiKeyError("malformed key: expected the form sf_<id>_<issued>_<signature>")
    _, key_id, issued_raw, signature = parts
    if not key_id or not signature:
        raise ApiKeyError("malformed key: empty identifier or signature")
    try:
        issued_at = int(issued_raw)
    except ValueError as exc:
        raise ApiKeyError("malformed key: the issue timestamp is not a number") from exc
    if issued_at <= 0 or issued_at > int(time.time()) + 300:
        raise ApiKeyError("malformed key: the issue timestamp is not in the past")

    expected = _sign(key_id, issued_at, secret)
    # Constant time: a leaky comparison here would let a caller discover a valid
    # signature one character at a time.
    if not hmac.compare_digest(expected, signature):
        raise ApiKeyError("this key's signature does not verify")

    age_days = (time.time() - issued_at) / 86_400
    if age_days > MAX_AGE_DAYS:
        raise ApiKeyError(
            f"this key was issued {int(age_days)} days ago and keys expire after {MAX_AGE_DAYS}; mint a new one"
        )
    return ApiKeyIdentity(tier=KEYED_TIER, key_id=key_id)


def identify(authorization: str | None, api_key_header: str | None) -> ApiKeyIdentity:
    """Resolve a request to an identity.

    No credential at all is not an error: it is the anonymous tier, which is the
    supported way to use this service. A credential that is *present and broken*
    is an error, because silently downgrading it would leave a caller wondering
    why their quota never went up.
    """
    token = None
    if api_key_header:
        token = api_key_header.strip()
    elif authorization:
        value = authorization.strip()
        if value.lower().startswith("bearer "):
            token = value[7:].strip()
        else:
            raise ApiKeyError("Authorization must use the Bearer scheme")
    if not token:
        return ANONYMOUS
    return verify(token)
