# DocuMind

DocuMind is a local-first document Q&A system. It loads PDFs, Markdown, and text files, retrieves relevant passages with citations, and can optionally draft grounded answers using an LLM.

## Development setup

Requires Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

```powershell
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy
```

## Web app

Start the local API and web interface together, then open `http://127.0.0.1:8000`:

```powershell
uv run uvicorn documind.api.main:app --reload
```

Drop in or browse for PDF, Markdown, and text files, then search the library. Turn on **Generate a grounded answer** to use the configured LLM. The selected provider receives the question and retrieved passages. Answers cite numbered source cards; select a citation to highlight its passage. The page adapts to narrow screens and the operating system's light or dark appearance setting. API docs are at `http://127.0.0.1:8000/docs`.

## Retrieval CLI

```powershell
uv run documind ingest path\to\document.pdf
uv run documind search "What does this document say?"
uv run documind ask "What does this document say?"
uv run documind ask --llm "What does this document say?"
uv run documind list
uv run documind delete <document-id>
```

The first real embedding may download the configured model (`all-MiniLM-L6-v2`). It loads only when ingestion or search first needs it. Search results below the configured threshold are omitted.

## REST API

The API provides `GET /health`, `POST /documents`, `GET /documents`, `DELETE /documents/{id}`, `POST /search`, and `POST /ask`. Uploads accept PDF, Markdown, and text files up to `DOCUMIND_MAX_UPLOAD_MB` (25 MB by default). CORS is disabled by default.

## LLM configuration

LLM use is disabled by default. Set `DOCUMIND_LLM_PROVIDER=ollama` for local Ollama or `DOCUMIND_LLM_PROVIDER=anthropic` for Anthropic's API. The Anthropic provider reads `ANTHROPIC_API_KEY` from the environment or ignored `.env` file. Search continues to work without either provider. When LLM use is enabled, retrieved passages are sent to the selected provider.

## Configuration

Settings are loaded from environment variables and `.env`. `.env.example` lists the supported settings; `.env` and the local `data/` directory are ignored by Git.

## Project status

Phase 7: optional grounded LLM answers, provider adapters, and clickable source citations. See the project brief for the staged roadmap.
