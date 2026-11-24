from pydantic import BaseModel, ConfigDict, Field


class OcrPageResult(BaseModel):
    """Text recognized from an individual PDF page using OCR."""

    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    text: str
    confidence: float = Field(ge=0, le=100)
    language: str = Field(min_length=1)
    dpi: int = Field(gt=0)
