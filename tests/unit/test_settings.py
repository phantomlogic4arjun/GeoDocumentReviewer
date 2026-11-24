from pathlib import Path

import pytest
from pydantic import ValidationError

from geo_document_reviewer.config.settings import PROJECT_ROOT, Settings, settings


def test_project_root_exists():
    assert PROJECT_ROOT.is_dir()


def test_project_root_contains_pyproject():
    assert (PROJECT_ROOT / "pyproject.toml").is_file()


def test_application_name():
    assert settings.app_name == "GeoDocumentReviewer"


def test_default_llm_provider():
    assert settings.llm_provider == "ollama"


def test_default_llm_model():
    assert settings.llm_model == "qwen3:8b"


def test_input_directories_are_inside_project():
    assert settings.reports_dir == PROJECT_ROOT / "input" / "reports"
    assert settings.specifications_dir == (PROJECT_ROOT / "input" / "specifications")
    assert settings.previous_revisions_dir == (PROJECT_ROOT / "input" / "previous_revisions")


def test_output_directory_is_inside_project():
    assert settings.output_dir == PROJECT_ROOT / "output"


def test_crs_template_path():
    expected_path = PROJECT_ROOT / "templates" / "PMEC_Comment_Resolution_Template.xlsx"
    assert settings.crs_template_path == expected_path


def test_configured_paths_are_path_objects():
    assert isinstance(settings.reports_dir, Path)
    assert isinstance(settings.output_dir, Path)
    assert isinstance(settings.crs_template_path, Path)


def test_default_ocr_language():
    assert settings.ocr_language == "eng"


def test_default_ocr_dpi():
    assert settings.ocr_dpi == 300


@pytest.mark.parametrize("dpi", [71, 601, 0, -1])
def test_rejects_invalid_ocr_dpi(dpi):
    with pytest.raises(ValidationError):
        Settings(ocr_dpi=dpi, _env_file=None)


def test_accepts_valid_ocr_dpi():
    configured_settings = Settings(ocr_dpi=400, _env_file=None)

    assert configured_settings.ocr_dpi == 400


def test_reads_ocr_environment_variables(monkeypatch):
    monkeypatch.setenv("OCR_LANGUAGE", "fra")
    monkeypatch.setenv("OCR_DPI", "400")
    monkeypatch.setenv(
        "TESSERACT_CMD",
        "/custom/path/tesseract",
    )

    configured_settings = Settings(_env_file=None)

    assert configured_settings.ocr_language == "fra"
    assert configured_settings.ocr_dpi == 400
    assert configured_settings.tesseract_cmd == "/custom/path/tesseract"


def test_tesseract_command_defaults_to_none():
    configured_settings = Settings(_env_file=None)

    assert configured_settings.tesseract_cmd is None
