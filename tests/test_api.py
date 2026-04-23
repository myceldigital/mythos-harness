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


def test_stream_route_emits_sse_events() -> None:
    client = TestClient(create_app())
    with client.stream(
        "POST",
        "/v1/mythos/stream",
        json={"query": "Build a migration plan", "thread_id": "stream-thread"},
    ) as response:
        assert response.status_code == 200
        body = "".join(chunk for chunk in response.iter_text())
    assert "event: token" in body
    assert "event: final" in body
    assert "event: done" in body


def test_metrics_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "mythos_http_requests_total" in response.text
