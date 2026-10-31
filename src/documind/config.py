"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env_int(name: str, default: int) -> int:
    """Read an integer setting and give a clear error for invalid values."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc


def _env_float(name: str, default: float) -> float:
    """Read a floating-point setting and give a clear error for invalid values."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {value!r}") from exc


@dataclass(frozen=True)
class Settings:
    """Settings shared by the CLI, API, and document pipeline."""

    data_dir: Path
    upload_dir: Path
    chroma_dir: Path
    sqlite_path: Path
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    score_threshold: float
    max_upload_mb: int
    search_mode: str
    reranker_model: str | None
    llm_provider: str
    ollama_url: str
    ollama_model: str
    anthropic_api_key: str | None
    anthropic_model: str
    anthropic_api_version: str
    llm_timeout_seconds: float
    llm_max_tokens: int

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from environment variables with local data defaults."""
        data_dir = Path(os.getenv("DOCUMIND_DATA_DIR", "data"))
        api_key = os.getenv("ANTHROPIC_API_KEY")
        return cls(
            data_dir=data_dir,
            upload_dir=Path(os.getenv("DOCUMIND_UPLOAD_DIR", str(data_dir / "uploads"))),
            chroma_dir=Path(os.getenv("DOCUMIND_CHROMA_DIR", str(data_dir / "chroma"))),
            sqlite_path=Path(os.getenv("DOCUMIND_SQLITE_PATH", str(data_dir / "documind.sqlite3"))),
            embedding_model=os.getenv("DOCUMIND_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            chunk_size=_env_int("DOCUMIND_CHUNK_SIZE", 800),
            chunk_overlap=_env_int("DOCUMIND_CHUNK_OVERLAP", 150),
            top_k=_env_int("DOCUMIND_TOP_K", 5),
            score_threshold=_env_float("DOCUMIND_SCORE_THRESHOLD", 0.25),
            max_upload_mb=_env_int("DOCUMIND_MAX_UPLOAD_MB", 25),
            search_mode=os.getenv("DOCUMIND_SEARCH_MODE", "vector").strip().lower(),
            reranker_model=(
                os.getenv("DOCUMIND_RERANKER_MODEL", "").strip() or None
            ),
            llm_provider=os.getenv("DOCUMIND_LLM_PROVIDER", "none").strip().lower(),
            ollama_url=os.getenv("DOCUMIND_OLLAMA_URL", "http://localhost:11434"),
            ollama_model=os.getenv("DOCUMIND_OLLAMA_MODEL", "gemma4"),
            anthropic_api_key=api_key.strip() if api_key and api_key.strip() else None,
            anthropic_model=os.getenv("DOCUMIND_ANTHROPIC_MODEL", "claude-sonnet-5-5"),
            anthropic_api_version=os.getenv("DOCUMIND_ANTHROPIC_API_VERSION", "2026-10-21"),
            llm_timeout_seconds=_env_float("DOCUMIND_LLM_TIMEOUT_SECONDS", 120.0),
            llm_max_tokens=_env_int("DOCUMIND_LLM_MAX_TOKENS", 1024),
        )


settings = Settings.from_env()
