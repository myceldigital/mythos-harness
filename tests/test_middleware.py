from fastapi.testclient import TestClient

from mythos_harness.config import Settings
from mythos_harness.main import create_app


def test_api_auth_blocks_without_key() -> None:
    settings = Settings(
        _env_file=None,
        api_auth_enabled=True,
        api_auth_keys="topsecret",
    )
    client = TestClient(create_app(settings))
    response = client.post(
        "/v1/mythos/complete",
        json={"query": "hello", "thread_id": "t1"},
    )
    assert response.status_code == 401


def test_api_auth_allows_with_key() -> None:
    settings = Settings(
        _env_file=None,
        api_auth_enabled=True,
        api_auth_keys="topsecret",
    )
    client = TestClient(create_app(settings))
    response = client.post(
        "/v1/mythos/complete",
        json={"query": "hello", "thread_id": "t1"},
        headers={"x-api-key": "topsecret"},
    )
    assert response.status_code == 200


def test_api_auth_allows_with_hashed_key() -> None:
    settings = Settings(
        _env_file=None,
        api_auth_enabled=True,
        api_auth_keys="",
        api_auth_key_hashes="53336a676c64c1396553b2b7c92f38126768827c93b64d9142069c10eda7a721",
    )
    client = TestClient(create_app(settings))
    response = client.post(
        "/v1/mythos/complete",
        json={"query": "hello", "thread_id": "t1"},
        headers={"x-api-key": "topsecret"},
    )
    assert response.status_code == 200


def test_rate_limit_returns_429_after_threshold() -> None:
    settings = Settings(
        _env_file=None,
        rate_limit_enabled=True,
        rate_limit_requests=1,
        rate_limit_window_s=60,
    )
    client = TestClient(create_app(settings))
    first = client.post(
        "/v1/mythos/complete",
        json={"query": "hello", "thread_id": "t1"},
    )
    second = client.post(
        "/v1/mythos/complete",
        json={"query": "hello again", "thread_id": "t2"},
    )
    assert first.status_code == 200
    assert second.status_code == 429


def test_request_id_header_is_present() -> None:
    settings = Settings(_env_file=None)
    client = TestClient(create_app(settings))
    response = client.post(
        "/v1/mythos/complete",
        json={"query": "hello", "thread_id": "t1"},
    )
    assert response.status_code == 200
    assert "x-request-id" in response.headers
