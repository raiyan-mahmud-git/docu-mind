"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from environment variables with local data defaults."""
        data_dir = Path(os.getenv("DOCUMIND_DATA_DIR", "data"))
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
        )


settings = Settings.from_env()
