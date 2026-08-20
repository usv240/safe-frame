from fastapi.testclient import TestClient

from agentic_core.api import ApiHooks, MemoryApiKeyStore, create_app


async def integrations() -> dict[str, dict[str, object]]:
    return {"google_vertex_ai": {"ok": True}, "parallel_search": {"ok": False}}


async def latest_eval() -> dict[str, object]:
    return {"split": "held-out", "counts": {"false_confident": 0}}


def client() -> TestClient:
    app = create_app(
        title="Test API",
        key_store=MemoryApiKeyStore(),
        key_pepper=b"a-test-pepper-with-enough-bytes",
        hooks=ApiHooks(integration_health=integrations, latest_evaluation=latest_eval),
    )
    return TestClient(app)


def test_judge_can_mint_key_without_email_and_call_api() -> None:
    api = client()
    minted = api.post("/v1/keys", json={"tier": "judge"})
    assert minted.status_code == 200
    key = minted.json()["data"]["key"]
    assert key.startswith("ak_live_")

    evaluation = api.get("/v1/eval/latest", headers={"Authorization": f"Bearer {key}"})
    assert evaluation.status_code == 200
    assert evaluation.json()["data"]["counts"]["false_confident"] == 0


def test_evaluation_key_requires_email() -> None:
    response = client().post("/v1/keys", json={"tier": "evaluation"})
    assert response.status_code == 422


def test_integration_health_is_public() -> None:
    response = client().get("/health/integrations")
    assert response.status_code == 200
    assert not response.json()["data"]["integrations"]["parallel_search"]["ok"]

