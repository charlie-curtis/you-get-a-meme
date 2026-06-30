from you_get_a_meme import __version__
from you_get_a_meme.server import app


def test_health() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version() -> None:
    assert __version__ == "0.1.0"
