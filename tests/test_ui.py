from fastapi.testclient import TestClient

from mythos_harness.main import create_app


def test_root_redirects_to_app() -> None:
    client = TestClient(create_app())
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/app"


def test_ui_shell_served() -> None:
    client = TestClient(create_app())
    response = client.get("/app")
    assert response.status_code == 200
    assert "Mythos Console" in response.text


def test_ui_static_assets_served() -> None:
    client = TestClient(create_app())
    css = client.get("/app/static/app.css")
    js = client.get("/app/static/app.js")
    assert css.status_code == 200
    assert js.status_code == 200
    assert "app-shell" in css.text
    assert "submitPrompt" in js.text
