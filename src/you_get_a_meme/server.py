from __future__ import annotations

import os
from typing import Annotated

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


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


TEMPLATE_SEEDS = [
    MemeCandidate(
        name="Drake Hotline Bling",
        fit="Rejecting the obvious bad option in favor of the surprisingly better one.",
        caption_idea="Top: forcing the thing that never works. Bottom: doing the tiny sane fix.",
        confidence=0.82,
    ),
    MemeCandidate(
        name="Distracted Boyfriend",
        fit="A person or team abandoning what they should focus on for a tempting distraction.",
        caption_idea="Partner: the important task. Boyfriend: you. Other person: the shiny distraction.",
        confidence=0.76,
    ),
    MemeCandidate(
        name="Two Buttons",
        fit="Choosing between two stressful, mutually awkward options.",
        caption_idea="Button one: ship it. Button two: rewrite the whole thing at midnight.",
        confidence=0.72,
    ),
]


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


@app.post("/api/memes/search")
def search_memes(request: SituationRequest) -> MemeSearchResponse:
    situation = request.situation.strip()
    return MemeSearchResponse(situation=situation, candidates=TEMPLATE_SEEDS)


def main() -> None:
    host = os.environ.get("YGAM_BACKEND_HOST", "127.0.0.1")
    port = int(os.environ.get("YGAM_BACKEND_PORT", "8765"))
    uvicorn.run("you_get_a_meme.server:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
