"""Typer CLI for local document ingestion and search."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, NoReturn

import typer

from documind.config import Settings
from documind.ingest import delete_document
from documind.logging_config import configure_logging
from documind.models import Document, SearchResult
from documind.runtime import Runtime, create_runtime

app = typer.Typer(no_args_is_help=True, help="Index local documents and search their passages.")


def _make_runtime() -> Runtime:
    """Create a command-scoped runtime; kept separate to simplify CLI tests."""
    return create_runtime(Settings.from_env())


def _document_line(document: Document) -> str:
    return (
        f"{document.id}  {document.filename}  "
        f"{document.pages} pages  {document.chunk_count} chunks"
    )


def _result_lines(results: list[SearchResult]) -> list[str]:
    lines: list[str] = []
    for result in results:
        snippet = " ".join(result.chunk.text.split())
        if len(snippet) > 300:
            snippet = snippet[:297].rstrip() + "..."
        lines.append(
            f"[{result.rank}] score={result.score:.3f}  "
            f"{result.chunk.filename}, page {result.chunk.page_number}\n{snippet}"
        )
    return lines


def _fail(message: str) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=1)


@app.command()
def ingest(
    path: Annotated[Path, typer.Argument(help="PDF, Markdown, or text file to index")],
) -> None:
    """Index a local document file."""
    try:
        runtime = _make_runtime()
    except Exception as exc:
        _fail(str(exc))
    try:
        document = runtime.ingestor.ingest_file(path)
        typer.echo(
            f"Indexed {document.filename}: {document.pages} pages, "
            f"{document.chunk_count} chunks\nID: {document.id}"
        )
    except (OSError, ValueError, RuntimeError) as exc:
        _fail(str(exc))
    finally:
        runtime.close()


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Question or phrase to search for")],
    top_k: Annotated[int | None, typer.Option(min=1, help="Maximum results to show")] = None,
) -> None:
    """Search indexed documents and print passage citations."""
    try:
        runtime = _make_runtime()
    except Exception as exc:
        _fail(str(exc))
    try:
        settings = Settings.from_env()
        results = runtime.retriever.search(query, top_k or settings.top_k)
        if not results:
            typer.echo("No relevant passage found.")
            return
        typer.echo("\n\n".join(_result_lines(results)))
    except (ValueError, RuntimeError) as exc:
        _fail(str(exc))
    finally:
        runtime.close()


@app.command()
def ask(
    query: Annotated[str, typer.Argument(help="Question to answer from indexed documents")],
    top_k: Annotated[int | None, typer.Option(min=1, help="Maximum passages to retrieve")] = None,
    use_llm: Annotated[bool, typer.Option("--llm", help="Generate a grounded LLM answer")] = False,
) -> None:
    """Answer from retrieved passages, optionally using the configured LLM."""
    try:
        runtime = _make_runtime()
    except Exception as exc:
        _fail(str(exc))
    try:
        settings = Settings.from_env()
        answer = runtime.qa.ask(query, top_k or settings.top_k, use_llm=use_llm)
        typer.echo(answer.text)
        for index, result in enumerate(answer.sources, start=1):
            typer.echo(
                f"[{index}] {result.chunk.filename}, page {result.chunk.page_number} "
                f"(score {result.score:.3f})"
            )
    except (ValueError, RuntimeError) as exc:
        _fail(str(exc))
    finally:
        runtime.close()

@app.command("list")
def list_documents() -> None:
    """List indexed documents."""
    try:
        runtime = _make_runtime()
    except Exception as exc:
        _fail(str(exc))
    try:
        documents = runtime.registry.list_documents()
        if not documents:
            typer.echo("No documents indexed.")
            return
        for document in documents:
            typer.echo(_document_line(document))
    finally:
        runtime.close()


@app.command()
def delete(
    doc_id: Annotated[str, typer.Argument(help="Document ID shown by the list command")],
) -> None:
    """Delete a document and all of its stored chunks."""
    try:
        runtime = _make_runtime()
    except Exception as exc:
        _fail(str(exc))
    try:
        if delete_document(doc_id, runtime.registry, runtime.vector_store):
            typer.echo(f"Deleted document {doc_id}.")
        else:
            typer.echo(f"Document {doc_id} was not found.")
    finally:
        runtime.close()


def main() -> None:
    """Run the CLI entry point."""
    configure_logging()
    app()
