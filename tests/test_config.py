from pathlib import Path

import pytest

from documind.config import Settings


def test_ocr_settings_are_loaded_from_environment(monkeypatch, tmp_path: Path) -> None:
    tessdata = tmp_path / "tessdata"
    monkeypatch.setenv("DOCUMIND_OCR_ENABLED", "false")
    monkeypatch.setenv("DOCUMIND_OCR_LANGUAGE", "eng+fra")
    monkeypatch.setenv("DOCUMIND_OCR_TESSDATA", str(tessdata))

    settings = Settings.from_env()

    assert settings.ocr_enabled is False
    assert settings.ocr_language == "eng+fra"
    assert settings.ocr_tessdata == tessdata


def test_ocr_setting_rejects_invalid_boolean(monkeypatch) -> None:
    monkeypatch.setenv("DOCUMIND_OCR_ENABLED", "sometimes")

    with pytest.raises(ValueError, match="must be true or false"):
        Settings.from_env()
