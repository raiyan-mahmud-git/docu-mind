"""Structured JSON logging for DocuMind application events."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    """Format application log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        event: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            event["stack"] = self.formatStack(record.stack_info)
        return json.dumps(event, ensure_ascii=False)


def configure_logging() -> None:
    """Configure structured output for DocuMind's logger hierarchy."""
    level_name = os.getenv("DOCUMIND_LOG_LEVEL", "INFO").strip().upper()
    level = logging.getLevelName(level_name)
    if not isinstance(level, int):
        raise ValueError(f"DOCUMIND_LOG_LEVEL must be a logging level, got {level_name!r}")

    logger = logging.getLogger("documind")
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
