from pathlib import Path

from geo_document_reviewer.config.settings import PROJECT_ROOT, settings


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
