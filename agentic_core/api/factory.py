"""FastAPI factory implementing the common public contract from PLAN/03."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Awaitable, Callable, Mapping

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agentic_core.api.keys import (
    ApiKeyRecord,
    ApiKeyStore,
    KeyTier,
    authenticate_key,
    mint_key,
)

IntegrationHealth = Callable[[], Awaitable[Mapping[str, Mapping[str, object]]]]
LatestEvaluation = Callable[[], Awaitable[Mapping[str, object]]]


@dataclass(frozen=True, slots=True)
class ApiHooks:
    integration_health: IntegrationHealth
    latest_evaluation: LatestEvaluation


class KeyRequest(BaseModel):
    tier: KeyTier
    email: str | None = None


def create_app(
    *,
    title: str,
    key_store: ApiKeyStore,
    key_pepper: bytes,
    hooks: ApiHooks,
) -> FastAPI:
    app = FastAPI(title=title, version="0.1.0")

    async def require_key(authorization: str | None = Header(default=None)) -> ApiKeyRecord:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="A Bearer API key is required.")
        record = authenticate_key(
            authorization.removeprefix("Bearer ").strip(),
            pepper=key_pepper,
            store=key_store,
        )
        if record is None:
            raise HTTPException(status_code=401, detail="The API key is invalid or expired.")
        return record

    @app.exception_handler(HTTPException)
    async def http_error(_request: object, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "ok": False,
                "error": {
                    "code": "unauthorized" if exc.status_code == 401 else "request_error",
                    "message": str(exc.detail),
                    "fix": "Mint a judge key at POST /v1/keys and send it as a Bearer token.",
                    "docs": "/docs",
                },
                "meta": {"request_id": "req_" + secrets.token_hex(10)},
            },
        )

    @app.get("/health")
    async def health() -> dict[str, object]:
        return {"ok": True, "data": {"status": "healthy"}}

    @app.get("/health/integrations")
    async def health_integrations() -> dict[str, object]:
        return {"ok": True, "data": {"integrations": await hooks.integration_health()}}

    @app.post("/v1/keys")
    async def create_key(request: KeyRequest) -> dict[str, object]:
        if request.tier == "evaluation" and not request.email:
            raise HTTPException(status_code=422, detail="An email is required for evaluation keys.")
        raw, record = mint_key(tier=request.tier, pepper=key_pepper, store=key_store)
        return {
            "ok": True,
            "data": {
                "key": raw,
                "tier": record.tier,
                "expires_at": record.expires_at.isoformat(),
                "daily_limit": record.daily_limit,
            },
            "meta": {"request_id": "req_" + secrets.token_hex(10)},
        }

    @app.get("/v1/eval/latest")
    async def latest_eval(_key: ApiKeyRecord = Depends(require_key)) -> dict[str, object]:
        return {"ok": True, "data": await hooks.latest_evaluation()}

    app.state.require_key = require_key
    return app

