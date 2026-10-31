import json
import logging

from documind.logging_config import JsonFormatter, configure_logging


def test_json_formatter_emits_structured_fields() -> None:
    record = logging.LogRecord(
        "documind.ingest", logging.INFO, "ingest.py", 20, "Indexed %s pages", (3,), None
    )

    event = json.loads(JsonFormatter().format(record))

    assert event["level"] == "INFO"
    assert event["logger"] == "documind.ingest"
    assert event["message"] == "Indexed 3 pages"
    assert event["timestamp"].endswith("Z")


def test_configure_logging_sets_level_and_json_formatter(monkeypatch) -> None:
    monkeypatch.setenv("DOCUMIND_LOG_LEVEL", "DEBUG")

    configure_logging()
    logger = logging.getLogger("documind")

    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0].formatter, JsonFormatter)

