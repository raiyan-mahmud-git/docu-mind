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

## Retrieval CLI

Ingest a document, search it, list indexed files, and delete documents by the ID shown by `list`:

```powershell
uv run documind ingest path\to\document.pdf
uv run documind search "What does this document say?"
uv run documind list
uv run documind delete <document-id>
```

The first real embedding may download the configured model (`all-MiniLM-L6-v2`). The model loads only on the first ingestion or search command that needs it. Results include the passage rank, similarity score, filename, and one-based page number. If the best match is below the configured threshold, search reports that no relevant passage was found.

To try the CLI with the included sample file:

```powershell
uv run documind ingest tests\fixtures\sample.txt
uv run documind search "How can a river shape a valley?"
uv run documind list
```

## Configuration

Settings use environment variables with defaults suitable for local development. `.env.example` lists the supported settings; `.env` and the local `data/` directory are ignored by Git.

## Project status

Phase 4: idempotent ingestion, semantic retrieval, and the retrieval-only CLI. See the project brief for the staged roadmap.
