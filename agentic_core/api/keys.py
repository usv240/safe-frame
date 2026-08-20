"""API-key primitives. Plaintext keys are returned once and never stored."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol

KeyTier = Literal["evaluation", "judge"]


@dataclass(frozen=True, slots=True)
class ApiKeyRecord:
    key_id: str
    digest: str
    tier: KeyTier
    expires_at: datetime
    daily_limit: int


class ApiKeyStore(Protocol):
    def put(self, record: ApiKeyRecord) -> None: ...

    def get(self, digest: str) -> ApiKeyRecord | None: ...


class MemoryApiKeyStore:
    """Test/local store. Production deployments replace this with a durable store."""

    def __init__(self) -> None:
        self._records: dict[str, ApiKeyRecord] = {}

    def put(self, record: ApiKeyRecord) -> None:
        self._records[record.digest] = record

    def get(self, digest: str) -> ApiKeyRecord | None:
        return self._records.get(digest)


def key_digest(key: str, pepper: bytes) -> str:
    return hmac.new(pepper, key.encode("utf-8"), hashlib.sha256).hexdigest()


def mint_key(*, tier: KeyTier, pepper: bytes, store: ApiKeyStore) -> tuple[str, ApiKeyRecord]:
    raw = f"ak_live_{secrets.token_hex(16)}"
    now = datetime.now(UTC)
    days, limit = (60, 2_000) if tier == "judge" else (30, 500)
    record = ApiKeyRecord(
        key_id="key_" + secrets.token_hex(10),
        digest=key_digest(raw, pepper),
        tier=tier,
        expires_at=now + timedelta(days=days),
        daily_limit=limit,
    )
    store.put(record)
    return raw, record


def authenticate_key(raw: str, *, pepper: bytes, store: ApiKeyStore) -> ApiKeyRecord | None:
    if not raw.startswith("ak_live_"):
        return None
    record = store.get(key_digest(raw, pepper))
    if record is None or record.expires_at <= datetime.now(UTC):
        return None
    return record

