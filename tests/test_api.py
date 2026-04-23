from fastapi.testclient import TestClient

from mythos_harness.main import create_app


def test_healthz() -> None:
    client = TestClient(create_app())
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz() -> None:
    client = TestClient(create_app())
    response = client.get("/readyz")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "checks" in payload


def test_complete_route_smoke() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/mythos/complete",
        json={"query": "Build a migration plan", "thread_id": "test-thread"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["thread_id"] == "test-thread"
    assert isinstance(payload["final_answer"], str)
    assert payload["loops"] >= 1
    assert "overall" in payload["confidence_summary"]


def test_metrics_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "mythos_http_requests_total" in response.text
