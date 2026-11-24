from pathlib import Path

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

    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen3:8b"

    reports_dir: Path = PROJECT_ROOT / "input" / "reports"
    specifications_dir: Path = PROJECT_ROOT / "input" / "specifications"
    previous_revisions_dir: Path = PROJECT_ROOT / "input" / "previous_revisions"
    output_dir: Path = PROJECT_ROOT / "output"

    crs_template_path: Path = PROJECT_ROOT / "templates" / "PMEC_Comment_Resolution_Template.xlsx"


settings = Settings()
