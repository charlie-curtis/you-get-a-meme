from __future__ import annotations

import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path

import httpx

from you_get_a_meme.catalog import PROJECT_ROOT, MemeTemplate, load_templates


OLLAMA_URL = os.environ.get("YGAM_OLLAMA_URL", "http://127.0.0.1:11434")
EMBEDDING_MODEL = os.environ.get("YGAM_EMBEDDING_MODEL", "mxbai-embed-large")
EMBEDDING_TIMEOUT_SECONDS = float(os.environ.get("YGAM_EMBEDDING_TIMEOUT_SECONDS", "20"))
DEFAULT_CACHE_PATH = PROJECT_ROOT / "data" / "cache" / "template_embeddings.json"


class EmbeddingCacheUnavailable(RuntimeError):
    pass


def embed_text(text: str) -> list[float]:
    response = httpx.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBEDDING_MODEL, "prompt": text},
        timeout=EMBEDDING_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["embedding"]


def build_embedding_record(template: MemeTemplate) -> dict:
    return {
        "id": template.id,
        "name": template.name,
        "embedding_text": template.embedding_text,
        "embedding": embed_text(template.embedding_text),
    }


def build_embedding_cache(cache_path: Path = DEFAULT_CACHE_PATH) -> dict:
    templates = load_templates()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache = {
        "generated_at": datetime.now(UTC).isoformat(),
        "model": EMBEDDING_MODEL,
        "templates": [build_embedding_record(template) for template in templates],
    }
    cache_path.write_text(json.dumps(cache, indent=2) + "\n")
    return cache


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(left_value * right_value for left_value, right_value in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def load_embedding_cache(cache_path: Path = DEFAULT_CACHE_PATH) -> dict:
    if not cache_path.exists():
        raise EmbeddingCacheUnavailable(f"Embedding cache not found: {cache_path}")
    return json.loads(cache_path.read_text())


def rank_templates_by_embedding(
    situation: str,
    *,
    cache_path: Path = DEFAULT_CACHE_PATH,
    limit: int = 8,
) -> list[tuple[MemeTemplate, float]]:
    templates_by_id = {template.id: template for template in load_templates()}
    cache = load_embedding_cache(cache_path)
    situation_embedding = embed_text(situation)

    ranked = []
    for record in cache.get("templates", []):
        template = templates_by_id.get(record.get("id"))
        embedding = record.get("embedding")
        if template is None or not isinstance(embedding, list):
            continue
        ranked.append((template, cosine_similarity(situation_embedding, embedding)))

    return sorted(ranked, key=lambda item: item[1], reverse=True)[:limit]


def main() -> None:
    cache = build_embedding_cache()
    print(
        f"Embedded {len(cache['templates'])} templates with {cache['model']} "
        f"into {DEFAULT_CACHE_PATH}"
    )


if __name__ == "__main__":
    main()
