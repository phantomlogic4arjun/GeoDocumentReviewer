from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "GeoDocumentReviewer"
    environment: str = "development"

    # Existing local model configuration remains unchanged.
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen3:8b"

    # Cloud review configuration.
    openrouter_api_key: str | None = Field(default=None, repr=False)
    openrouter_model: str = "qwen/qwen3.8-flash"

    ocr_language: str = "eng"
    ocr_dpi: int = Field(default=300, ge=72, le=600)
    tesseract_cmd: str | None = None

    reports_dir: Path = PROJECT_ROOT / "input" / "reports"
    specifications_dir: Path = PROJECT_ROOT / "input" / "specifications"
    previous_revisions_dir: Path = PROJECT_ROOT / "input" / "previous_revisions"
    output_dir: Path = PROJECT_ROOT / "output"
    crs_template_path: Path = PROJECT_ROOT / "templates" / "PMEC_Comment_Resolution_Template.xlsx"


settings = Settings()
