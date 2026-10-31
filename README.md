# DocuMind

DocuMind is a local-first document Q&A system. It loads PDFs, Markdown, and text files, retrieves relevant passages with citations, and will optionally use an LLM to draft grounded answers in a later phase.

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

Drop in or browse for PDF, Markdown, and text files, then search the library. Results include the source filename and one-based page number. The page adapts to narrow screens and the operating system's light or dark appearance setting. The API's interactive reference remains at `http://127.0.0.1:8000/docs`.

## Retrieval CLI

```powershell
uv run documind ingest path\to\document.pdf
uv run documind search "What does this document say?"
uv run documind list
uv run documind delete <document-id>
```

The first real embedding may download the configured model (`all-MiniLM-L6-v2`). It loads only when ingestion or search first needs it. Results below the configured threshold are omitted.

## REST API

The API provides `GET /health`, `POST /documents`, `GET /documents`, `DELETE /documents/{id}`, and `POST /search`. Uploads accept PDF, Markdown, and text files up to `DOCUMIND_MAX_UPLOAD_MB` (25 MB by default). CORS is disabled unless configured in a later phase.

## Configuration

Settings use environment variables with defaults suitable for local development. `.env.example` lists the supported settings; `.env` and the local `data/` directory are ignored by Git.

## Project status

Phase 6: local browser interface for document upload, management, and cited search. See the project brief for the staged roadmap.
