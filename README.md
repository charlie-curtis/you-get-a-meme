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
- Ollama with `llama3.2:3b` for local LLM calls
- Electron for the desktop window

## First Milestone

1. Seed a small curated template database.
2. Search templates from a user situation.
3. Generate candidate captions with Ollama.
4. Render a downloadable meme image.

## Development

Install the Python and Electron dependencies, then start the desktop shell:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
npm install
npm start
```

Electron launches the Python API locally and loads the renderer UI. The first implementation slice has placeholder meme matches; the next slice should replace those with the template metadata model and an Ollama client.

The app expects Ollama to be running separately when you want model-backed results:

```bash
ollama serve
ollama pull llama3.2:3b
```

If Ollama is unavailable or the model call times out, the app falls back to starter template results instead of hanging.
