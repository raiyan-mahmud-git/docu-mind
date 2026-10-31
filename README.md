# DocuMind

DocuMind is a local-first document Q&A system. It will load PDFs, Markdown, and text files, retrieve relevant passages with citations, and optionally use an LLM to draft grounded answers.

## Development setup

Requires Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

```powershell
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy
```

## Configuration

Settings use environment variables with defaults suitable for local development. Copy `.env.example` to `.env` to record local choices; secrets and `.env` are ignored by Git. The configuration module reads process environment variables directly.

## Loading and chunking

Loaders support searchable text in PDF, Markdown, and UTF-8 plain-text files. PDF page numbers are one-based and remain accurate even when blank pages are skipped. Scanned PDFs without a text layer are not supported. Chunking keeps paragraphs and sentences together when possible, limits chunks by character count, overlaps neighboring chunks, and preserves the source page number.

```powershell
uv run python -c "from documind.chunking import chunk_pages; from documind.loaders import load_pdf; print(chunk_pages(load_pdf('sample.pdf'), 'document-sha256', 'sample.pdf'))"
```

## Project status

Phase 2: document loaders and deterministic text chunking. See the project brief for the staged roadmap.
