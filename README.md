# You Get a Meme

Describe the situation. Get the meme.

You Get a Meme is a local-first meme finder and generator. The app helps you describe a situation in plain language, finds meme formats that fit the context, asks a local LLM for captions, and renders the final image on your machine.

## Direction

- Search meme templates by situation, not just by template name.
- Keep the template library local and explainable.
- Use Ollama for local caption generation.
- Render output locally with Python image tooling.
- Ship as a standalone desktop app once the core loop feels good.

## Planned Stack

- Python app backend
- FastAPI for local API routes
- SQLite for template metadata
- Pillow for meme rendering
- Ollama for local LLM calls
- pywebview for the desktop window

## First Milestone

1. Seed a small curated template database.
2. Search templates from a user situation.
3. Generate candidate captions with Ollama.
4. Render a downloadable meme image.

## Development

This repo is just scaffolded for now. The first implementation slice will likely start with the template metadata model and an Ollama client.
