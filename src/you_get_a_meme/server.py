from __future__ import annotations

import json
import os
from typing import Annotated

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from you_get_a_meme.catalog import load_templates


class SituationRequest(BaseModel):
    situation: Annotated[str, Field(min_length=3, max_length=400)]


class MemeCandidate(BaseModel):
    name: str
    fit: str
    caption_idea: str
    confidence: float


class MemeSearchResponse(BaseModel):
    situation: str
    candidates: list[MemeCandidate]
    source: str
    model: str


OLLAMA_URL = os.environ.get("YGAM_OLLAMA_URL", "http://127.0.0.1:11434")
CHAT_MODEL = os.environ.get("YGAM_CHAT_MODEL", "llama3.2:3b")
OLLAMA_TIMEOUT_SECONDS = float(os.environ.get("YGAM_OLLAMA_TIMEOUT_SECONDS", "20"))


def fallback_candidates() -> list[MemeCandidate]:
    return [
        MemeCandidate(
            name=template.name,
            fit=template.description,
            caption_idea=template.caption_pattern,
            confidence=0.7,
        )
        for template in load_templates()
    ]


def template_catalog_for_prompt() -> str:
    return "\n".join(template.prompt_line for template in load_templates())


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

    return normalized


def ask_ollama_for_candidates(situation: str) -> list[MemeCandidate]:
    system_prompt = (
        "You pick meme templates for a user's situation. "
        "Choose only from the provided templates. "
        "Return strict JSON with one key, candidates. "
        "Each candidate must have name, fit, caption_idea, and confidence. "
        "The fit value must be a short sentence, not a boolean. "
        "The caption_idea value must be one short string, not a list. "
        "Confidence is a number from 0 to 1."
    )
    user_prompt = (
        f"Situation: {situation}\n\n"
        f"Available templates:\n{template_catalog_for_prompt()}\n\n"
        "Return the 3 best matches as JSON. Write fresh caption ideas for this exact situation."
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

    try:
        candidates = ask_ollama_for_candidates(situation)
    except httpx.HTTPError:
        candidates = []

    if candidates:
        return MemeSearchResponse(
            situation=situation,
            candidates=candidates,
            source="ollama",
            model=CHAT_MODEL,
        )

    return MemeSearchResponse(
        situation=situation,
        candidates=fallback_candidates(),
        source="fallback",
        model=CHAT_MODEL,
    )


def main() -> None:
    host = os.environ.get("YGAM_BACKEND_HOST", "127.0.0.1")
    port = int(os.environ.get("YGAM_BACKEND_PORT", "8765"))
    uvicorn.run("you_get_a_meme.server:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
