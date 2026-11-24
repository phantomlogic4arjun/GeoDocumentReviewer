from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class PdfDocument(BaseModel):
    """Metadata describing a validated PDF document."""

    model_config = ConfigDict(frozen=True)

    file_path: Path
    file_name: str = Field(min_length=1)
    file_size_bytes: int = Field(gt=0)
    page_count: int = Field(gt=0)
    metadata: dict[str, str | None] = Field(default_factory=dict)
