from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from geo_document_reviewer.ocr.models import OcrPageResult


class ProcessedPage(BaseModel):
    """Combined text, OCR, and visual metadata for one PDF page."""

    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    extracted_text: str
    requires_ocr: bool = False
    ocr_result: OcrPageResult | None = None

    page_width: float | None = Field(default=None, gt=0)
    page_height: float | None = Field(default=None, gt=0)
    embedded_image_count: int = Field(default=0, ge=0)
    vector_drawing_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_ocr_result(self):
        if self.ocr_result is not None:
            if self.ocr_result.page_number != self.page_number:
                raise ValueError("OCR result page number must match the processed page number.")

            if not self.requires_ocr:
                raise ValueError(
                    "OCR result cannot be provided for a page that does not require OCR."
                )

        return self

    @property
    def review_text(self) -> str:
        """Return the text selected for downstream review."""
        if self.ocr_result is not None and self.ocr_result.text.strip():
            return self.ocr_result.text

        return self.extracted_text

    @property
    def has_visual_content(self) -> bool:
        """Indicate whether the page contains images or vector drawings."""
        return self.embedded_image_count > 0 or self.vector_drawing_count > 0

    @property
    def is_landscape(self) -> bool | None:
        """Identify landscape pages when dimensions are available."""
        if self.page_width is None or self.page_height is None:
            return None

        return self.page_width > self.page_height


class ProcessedDocument(BaseModel):
    """Complete document content after extraction and optional OCR processing."""

    model_config = ConfigDict(frozen=True)

    source_path: Path
    file_name: str = Field(min_length=1)
    page_count: int = Field(gt=0)
    pages: tuple[ProcessedPage, ...]

    @model_validator(mode="after")
    def validate_pages(self):
        if len(self.pages) != self.page_count:
            raise ValueError("page_count must match the number of processed page records.")

        expected_page_numbers = tuple(range(1, self.page_count + 1))
        actual_page_numbers = tuple(page.page_number for page in self.pages)

        if actual_page_numbers != expected_page_numbers:
            raise ValueError("Processed page numbers must be sequential, starting at 1.")

        return self

    @property
    def pages_processed_with_ocr(self) -> tuple[int, ...]:
        """Return page numbers for which OCR results are available."""
        return tuple(page.page_number for page in self.pages if page.ocr_result is not None)

    @property
    def review_text_by_page(self) -> dict[int, str]:
        """Return the selected review text indexed by original PDF page number."""
        return {page.page_number: page.review_text for page in self.pages}

    @property
    def pages_with_visual_content(self) -> tuple[int, ...]:
        """Return page numbers containing images or vector drawings."""
        return tuple(page.page_number for page in self.pages if page.has_visual_content)

    @property
    def landscape_pages(self) -> tuple[int, ...]:
        """Return page numbers identified as landscape."""
        return tuple(page.page_number for page in self.pages if page.is_landscape is True)
