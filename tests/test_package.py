import json

from you_get_a_meme import __version__
from you_get_a_meme.catalog import load_templates
from you_get_a_meme.embeddings import cosine_similarity, rank_templates_by_embedding
from you_get_a_meme.server import MemeCandidate, app, apply_retrieval_scores, parse_llm_candidates


def test_health() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_load_templates_from_text_file() -> None:
    templates = load_templates()

    assert [template.id for template in templates] == [
        "drake-hotline-bling",
        "distracted-boyfriend",
        "two-buttons",
    ]
    assert templates[0].name == "Drake Hotline Bling"
    assert "preference" in templates[0].tags


def test_cosine_similarity() -> None:
    assert cosine_similarity([1, 0], [1, 0]) == 1
    assert cosine_similarity([1, 0], [0, 1]) == 0


def test_rank_templates_by_embedding(tmp_path, monkeypatch) -> None:
    cache_path = tmp_path / "embeddings.json"
    cache_path.write_text(
        json.dumps(
            {
                "model": "test",
                "templates": [
                    {"id": "drake-hotline-bling", "embedding": [1, 0]},
                    {"id": "two-buttons", "embedding": [0, 1]},
                ],
            }
        )
    )
    monkeypatch.setattr("you_get_a_meme.embeddings.embed_text", lambda _text: [0, 1])

    ranked = rank_templates_by_embedding("hard choice", cache_path=cache_path)

    assert ranked[0][0].id == "two-buttons"
    assert ranked[0][1] == 1


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


def test_parse_llm_candidates_accepts_missing_confidence() -> None:
    candidates = parse_llm_candidates(
        """
        {
          "candidates": [
            {
              "name": "Two Buttons",
              "fit": "A stressful choice.",
              "caption_idea": "Button one. Button two."
            }
          ]
        }
        """
    )

    assert len(candidates) == 1
    assert candidates[0].confidence == 0


def test_apply_retrieval_scores_overrides_model_confidence() -> None:
    two_buttons = next(template for template in load_templates() if template.name == "Two Buttons")
    candidates = [
        MemeCandidate(
            name="Two Buttons",
            fit="A stressful choice.",
            caption_idea="Button one. Button two.",
            confidence=0.99,
        )
    ]

    scored = apply_retrieval_scores(candidates, [(two_buttons, 0.42)])

    assert scored[0].confidence == 0.42


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

    def unavailable(_situation: str, _ranked_templates):
        return []

    monkeypatch.setattr("you_get_a_meme.server.ask_ollama_for_candidates", unavailable)

    client = TestClient(app)
    response = client.post("/api/memes/search", json={"situation": "a tiny fix breaks everything"})

    assert response.status_code == 200
    assert response.json()["source"] == "fallback"
    assert response.json()["model"] == "llama3.2:3b"
    assert response.json()["retrieval"] in {"embeddings", "all-templates"}
    assert len(response.json()["candidates"]) == 3


def test_version() -> None:
    assert __version__ == "0.1.0"
