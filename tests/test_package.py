from you_get_a_meme import __version__
from you_get_a_meme.server import app, parse_llm_candidates


def test_health() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_parse_llm_candidates() -> None:
    candidates = parse_llm_candidates(
        """
        {
          "candidates": [
            {
              "name": "Two Buttons",
              "fit": "A stressful choice.",
              "caption_idea": "Button one. Button two.",
              "confidence": 0.87
            }
          ]
        }
        """
    )

    assert len(candidates) == 1
    assert candidates[0].name == "Two Buttons"


def test_parse_llm_candidates_normalizes_common_model_shapes() -> None:
    candidates = parse_llm_candidates(
        """
        {
          "candidates": [
            {
              "name": "Distracted Boyfriend",
              "fit": true,
              "caption_idea": [
                "When a tiny CSS fix breaks the whole layout",
                "The important task vs the tempting quick fix"
              ],
              "confidence": 0.9
            }
          ]
        }
        """
    )

    assert len(candidates) == 1
    assert candidates[0].name == "Distracted Boyfriend"
    assert "strong fit" in candidates[0].fit
    assert " / " in candidates[0].caption_idea


def test_search_falls_back_when_ollama_is_unavailable(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    def unavailable(_situation: str):
        return []

    monkeypatch.setattr("you_get_a_meme.server.ask_ollama_for_candidates", unavailable)

    client = TestClient(app)
    response = client.post("/api/memes/search", json={"situation": "a tiny fix breaks everything"})

    assert response.status_code == 200
    assert response.json()["source"] == "fallback"
    assert response.json()["model"] == "llama3.2:3b"
    assert len(response.json()["candidates"]) == 3


def test_version() -> None:
    assert __version__ == "0.1.0"
