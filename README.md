# DocuMind

DocuMind is a local-first document Q&A system. It will load PDFs, Markdown, and text files, retrieve relevant passages with citations, and optionally use an LLM to draft grounded answers.

## Development setup

Requires Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

```powershell
uv sync --extra dev
uv run pytest
uv run ruff check .
```

## Configuration

Settings use environment variables with defaults suitable for local development. Copy `.env.example` to `.env` to record local choices; secrets and `.env` are ignored by Git. The configuration module reads process environment variables directly.

## Project status

Phase 0: project setup and configuration scaffold. See the project brief for the staged roadmap.
