from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PageText(BaseModel):
    """Text and visual metadata extracted from an individual PDF page."""

    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    text: str
    character_count: int = Field(ge=0)
    requires_ocr: bool = False

    page_width: float | None = Field(default=None, gt=0)
    page_height: float | None = Field(default=None, gt=0)
    embedded_image_count: int = Field(default=0, ge=0)
    vector_drawing_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_character_count(self):
        if self.character_count != len(self.text):
            raise ValueError("character_count must match the length of the extracted text.")
        return self

    @property
    def has_visual_content(self) -> bool:
        """Indicate whether the page contains images or vector drawings."""
        return self.embedded_image_count > 0 or self.vector_drawing_count > 0

    @property
    def is_landscape(self) -> bool | None:
        """Identify landscape pages when page dimensions are available."""
        if self.page_width is None or self.page_height is None:
            return None

        return self.page_width > self.page_height


class ExtractedDocument(BaseModel):
    """Text extraction results for an entire PDF document."""

    model_config = ConfigDict(frozen=True)

    source_path: Path
    file_name: str = Field(min_length=1)
    page_count: int = Field(gt=0)
    pages: tuple[PageText, ...]

    @model_validator(mode="after")
    def validate_pages(self):
        if len(self.pages) != self.page_count:
            raise ValueError("page_count must match the number of extracted page records.")

        expected_page_numbers = tuple(range(1, self.page_count + 1))
        actual_page_numbers = tuple(page.page_number for page in self.pages)

        if actual_page_numbers != expected_page_numbers:
            raise ValueError("Page numbers must be sequential, starting at 1.")

        return self

    @property
    def pages_requiring_ocr(self) -> tuple[int, ...]:
        """Return page numbers flagged as possible OCR candidates."""
        return tuple(page.page_number for page in self.pages if page.requires_ocr)
