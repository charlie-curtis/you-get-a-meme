from __future__ import annotations

import json
import os
from typing import Annotated

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from you_get_a_meme.catalog import MemeTemplate
from you_get_a_meme.catalog import load_templates
from you_get_a_meme.embeddings import EmbeddingCacheUnavailable, rank_templates_by_embedding


class SituationRequest(BaseModel):
    situation: Annotated[str, Field(min_length=3, max_length=400)]


class MemeCandidate(BaseModel):
    name: str
    fit: str
    caption_idea: str
    boxes: list[str]
    confidence: float


class MemeSearchResponse(BaseModel):
    situation: str
    candidates: list[MemeCandidate]
    source: str
    model: str
    retrieval: str


OLLAMA_URL = os.environ.get("YGAM_OLLAMA_URL", "http://127.0.0.1:11434")
CHAT_MODEL = os.environ.get("YGAM_CHAT_MODEL", "llama3.2:3b")
OLLAMA_TIMEOUT_SECONDS = float(os.environ.get("YGAM_OLLAMA_TIMEOUT_SECONDS", "20"))


def fallback_candidates(ranked_templates: list[tuple[MemeTemplate, float]] | None = None) -> list[MemeCandidate]:
    if ranked_templates:
        return [
            MemeCandidate(
                name=template.name,
                fit=template.description,
                caption_idea=template.caption_pattern,
                boxes=fallback_boxes(template),
                confidence=max(0, min(1, score)),
            )
            for template, score in ranked_templates
        ]

    return [
        MemeCandidate(
            name=template.name,
            fit=template.description,
            caption_idea=template.caption_pattern,
            boxes=fallback_boxes(template),
            confidence=0.7,
        )
        for template in load_templates()
    ]


def fallback_boxes(template: MemeTemplate) -> list[str]:
    if template.box_labels:
        return [f"[{label}]" for label in template.box_labels[: template.box_count]]
    return [f"[box {index + 1}]" for index in range(template.box_count)]


def template_catalog_for_prompt(ranked_templates: list[tuple[MemeTemplate, float]]) -> str:
    return "\n".join(
        f"{template.prompt_line} Retrieval score: {score:.3f}"
        for template, score in ranked_templates
    )


def parse_llm_candidates(content: str) -> list[MemeCandidate]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return []

    candidates = payload.get("candidates", [])
    if not isinstance(candidates, list):
        return []

    parsed = []
    for candidate in candidates[:3]:
        if not isinstance(candidate, dict):
            continue
        normalized = normalize_llm_candidate(candidate)
        try:
            parsed.append(MemeCandidate.model_validate(normalized))
        except ValueError:
            continue
    return parsed


def normalize_llm_candidate(candidate: dict) -> dict:
    normalized = dict(candidate)
    normalized.setdefault("confidence", 0)

    fit = normalized.get("fit")
    if isinstance(fit, bool):
        normalized["fit"] = (
            "The model marked this as a strong fit for the situation."
            if fit
            else "The model marked this as a weaker fit, but still related."
        )

    caption_idea = normalized.get("caption_idea")
    if isinstance(caption_idea, list):
        normalized["caption_idea"] = " / ".join(str(item) for item in caption_idea if item)

    boxes = normalized.get("boxes")
    if isinstance(boxes, dict):
        normalized["boxes"] = [str(value) for _, value in sorted(boxes.items())]
    elif isinstance(boxes, list):
        normalized["boxes"] = [str(item) for item in boxes if item]
    else:
        normalized["boxes"] = []

    return normalized


def candidate_score_by_name(ranked_templates: list[tuple[MemeTemplate, float]]) -> dict[str, float]:
    return {template.name: max(0, min(1, score)) for template, score in ranked_templates}


def template_by_name(ranked_templates: list[tuple[MemeTemplate, float]]) -> dict[str, MemeTemplate]:
    return {template.name: template for template, _score in ranked_templates}


def apply_retrieval_scores(
    candidates: list[MemeCandidate],
    ranked_templates: list[tuple[MemeTemplate, float]],
) -> list[MemeCandidate]:
    scores = candidate_score_by_name(ranked_templates)
    return [
        candidate.model_copy(update={"confidence": scores.get(candidate.name, candidate.confidence)})
        for candidate in candidates
    ]


def apply_template_box_counts(
    candidates: list[MemeCandidate],
    ranked_templates: list[tuple[MemeTemplate, float]],
) -> list[MemeCandidate]:
    templates = template_by_name(ranked_templates)
    normalized = []
    for candidate in candidates:
        template = templates.get(candidate.name)
        if template is None:
            normalized.append(candidate)
            continue

        boxes = candidate.boxes[: template.box_count]
        while len(boxes) < template.box_count:
            boxes.append("")
        normalized.append(candidate.model_copy(update={"boxes": boxes}))
    return normalized


def ask_ollama_for_candidates(
    situation: str,
    ranked_templates: list[tuple[MemeTemplate, float]],
) -> list[MemeCandidate]:
    system_prompt = (
        "You pick meme templates for a user's situation. "
        "Choose only from the provided templates. "
        "Return strict JSON with one key, candidates. "
        "Each candidate must have name, fit, caption_idea, and boxes. "
        "The fit value must be a short sentence, not a boolean. "
        "The caption_idea value must be one short string, not a list. "
        "The boxes value must be an array of strings. "
        "The boxes array length must match the template's text box count. "
        "Every boxes item must be non-empty and must follow the template's box labels in order. "
        "Do not include confidence scores."
    )
    user_prompt = (
        f"Situation: {situation}\n\n"
        f"Available templates, already ranked by embedding search:\n"
        f"{template_catalog_for_prompt(ranked_templates)}\n\n"
        "Return the 3 best matches as JSON. Write fresh caption ideas for this exact situation. "
        "Use only these keys for each candidate: name, fit, caption_idea, boxes. "
        "For example, if a template says box labels are first hard choice, second hard choice, "
        "anxious decision maker, return boxes in exactly that order."
    )

    response = httpx.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": CHAT_MODEL,
            "stream": False,
            "format": "json",
            "options": {
                "num_predict": 350,
                "temperature": 0.7,
            },
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=OLLAMA_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    content = response.json()["message"]["content"]
    return parse_llm_candidates(content)


app = FastAPI(title="You Get a Meme API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/ollama/health")
def ollama_health() -> dict[str, str]:
    try:
        response = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        response.raise_for_status()
    except httpx.HTTPError:
        return {"status": "offline", "model": CHAT_MODEL}

    return {"status": "ok", "model": CHAT_MODEL}


@app.post("/api/memes/search")
def search_memes(request: SituationRequest) -> MemeSearchResponse:
    situation = request.situation.strip()
    retrieval = "all-templates"

    try:
        ranked_templates = rank_templates_by_embedding(situation, limit=8)
        if ranked_templates:
            retrieval = "embeddings"
        else:
            ranked_templates = [(template, 0.7) for template in load_templates()]
    except (EmbeddingCacheUnavailable, httpx.HTTPError, ValueError):
        ranked_templates = [(template, 0.7) for template in load_templates()]

    try:
        candidates = ask_ollama_for_candidates(situation, ranked_templates)
    except httpx.HTTPError:
        candidates = []

    if candidates:
        candidates = apply_retrieval_scores(candidates, ranked_templates)
        candidates = apply_template_box_counts(candidates, ranked_templates)
        return MemeSearchResponse(
            situation=situation,
            candidates=candidates,
            source="ollama",
            model=CHAT_MODEL,
            retrieval=retrieval,
        )

    return MemeSearchResponse(
        situation=situation,
        candidates=fallback_candidates(ranked_templates),
        source="fallback",
        model=CHAT_MODEL,
        retrieval=retrieval,
    )


def main() -> None:
    host = os.environ.get("YGAM_BACKEND_HOST", "127.0.0.1")
    port = int(os.environ.get("YGAM_BACKEND_PORT", "8765"))
    uvicorn.run("you_get_a_meme.server:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
