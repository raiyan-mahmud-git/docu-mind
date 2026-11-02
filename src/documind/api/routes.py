"""HTTP endpoints for document management and retrieval."""



from __future__ import annotations

from functools import partial

# FastAPI dependency markers intentionally use callable defaults (B008).
# ruff: noqa: B008
from pathlib import Path, PureWindowsPath
from typing import cast
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from starlette.concurrency import run_in_threadpool

from documind.api.schemas import (
    AnswerResponse,
    AskRequest,
    DocumentResponse,
    ExtractedPageResponse,
    HealthResponse,
    PassageResponse,
    PDFTextExtractionResponse,
    SearchRequest,
    SearchResponse,
)
from documind.config import Settings
from documind.ingest import delete_document
from documind.loaders.pdf import extract_pdf_pages
from documind.models import Document
from documind.runtime import Runtime

router = APIRouter()
_ALLOWED_SUFFIXES = {
    ".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".md", ".txt"
}


def get_runtime(request: Request) -> Runtime:
    """Get the app's shared service bundle."""
    return cast(Runtime, request.app.state.runtime)


def get_settings(request: Request) -> Settings:
    """Get the app's immutable settings."""
    return cast(Settings, request.app.state.settings)


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report whether the API process is serving requests."""
    return HealthResponse()


@router.post(
    "/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    runtime: Runtime = Depends(get_runtime),
    settings: Settings = Depends(get_settings),
) -> DocumentResponse:
    """Upload and index a supported document or OCR-readable image."""
    raw_name = file.filename or ""
    filename = Path(PureWindowsPath(raw_name).name).name
    if not filename:
        raise HTTPException(status_code=400, detail="A filename is required")
    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type; upload a PDF, PNG, JPG, JPEG, BMP, TIFF, "
                "Markdown, or text file"
            ),
        )

    max_bytes = settings.max_upload_mb * 1024 * 1024
    contents = await file.read(max_bytes + 1)
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.max_upload_mb} MB upload limit",
        )
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    temporary_path = settings.upload_dir / f"{uuid4().hex}{suffix}"
    try:
        temporary_path.write_bytes(contents)
        document: Document = await run_in_threadpool(
            runtime.ingestor.ingest_file,
            temporary_path,
            filename,
        )
        return DocumentResponse.from_document(document)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        temporary_path.unlink(missing_ok=True)
        await file.close()


@router.post("/extract-text", response_model=PDFTextExtractionResponse)
async def extract_selected_pdf_text(
    file: UploadFile = File(...),
    pages: str = Form(...),
    settings: Settings = Depends(get_settings),
) -> PDFTextExtractionResponse:
    """Return selectable text or local OCR text from chosen PDF pages."""
    raw_name = file.filename or ""
    filename = Path(PureWindowsPath(raw_name).name).name
    if Path(filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Choose a PDF file")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    contents = await file.read(max_bytes + 1)
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.max_upload_mb} MB upload limit",
        )
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    temporary_path = settings.upload_dir / f"{uuid4().hex}.pdf"
    try:
        temporary_path.write_bytes(contents)
        total_pages, extracted_pages = await run_in_threadpool(
            partial(
                extract_pdf_pages,
                temporary_path,
                pages,
                ocr_enabled=settings.ocr_enabled,
                ocr_language=settings.ocr_language,
                ocr_tessdata=settings.ocr_tessdata,
                max_pages=20,
            )
        )
        return PDFTextExtractionResponse(
            total_pages=total_pages,
            pages=[
                ExtractedPageResponse(page_number=page.page_number, text=page.text)
                for page in extracted_pages
            ],
        )
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        temporary_path.unlink(missing_ok=True)
        await file.close()


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(
    runtime: Runtime = Depends(get_runtime),
) -> list[DocumentResponse]:
    """Return indexed documents newest first."""
    return [
        DocumentResponse.from_document(document)
        for document in runtime.registry.list_documents()
    ]


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_document(
    doc_id: str,
    runtime: Runtime = Depends(get_runtime),
) -> None:
    """Remove one document and all its stored passage vectors."""
    if not delete_document(doc_id, runtime.registry, runtime.vector_store):
        raise HTTPException(status_code=404, detail="Document not found")


@router.post("/search", response_model=SearchResponse)
def search_documents(
    payload: SearchRequest,
    runtime: Runtime = Depends(get_runtime),
    settings: Settings = Depends(get_settings),
) -> SearchResponse:
    """Return relevant passages with exact filename and page citations."""
    if not payload.query.strip():
        raise HTTPException(status_code=422, detail="Query must not be empty")
    try:
        results = runtime.retriever.search(payload.query, payload.top_k or settings.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    passages = [PassageResponse.from_result(result) for result in results]
    return SearchResponse(
        query=payload.query,
        results=passages,
        no_relevant_passage=not passages,
    )









@router.post("/ask", response_model=AnswerResponse)
def ask_documents(
    payload: AskRequest,
    runtime: Runtime = Depends(get_runtime),
    settings: Settings = Depends(get_settings),
) -> AnswerResponse:
    """Answer from retrieved passages, optionally through the configured LLM."""
    if not payload.query.strip():
        raise HTTPException(status_code=422, detail="Query must not be empty")
    try:
        answer = runtime.qa.ask(
            payload.query,
            payload.top_k or settings.top_k,
            use_llm=payload.use_llm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AnswerResponse.from_answer(answer)
