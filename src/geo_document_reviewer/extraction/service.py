import pymupdf

from geo_document_reviewer.extraction.models import (
    ExtractedDocument,
    PageText,
)
from geo_document_reviewer.ingestion.models import PdfDocument


class PdfExtractionError(Exception):
    """Raised when text cannot be extracted from a PDF."""


class PdfExtractionService:
    """Extracts page-level text and visual metadata from an ingested PDF."""

    def __init__(self, ocr_min_characters: int = 20) -> None:
        if ocr_min_characters < 1:
            raise ValueError("ocr_min_characters must be greater than zero.")

        self.ocr_min_characters = ocr_min_characters

    def extract(self, document: PdfDocument) -> ExtractedDocument:
        """Extract text and visual metadata from every PDF page."""

        path = document.file_path

        if not path.exists() or not path.is_file():
            raise PdfExtractionError(f"Source PDF is unavailable: {path}")

        try:
            with pymupdf.open(path) as pdf:
                if pdf.needs_pass:
                    raise PdfExtractionError("PDF is password-protected and cannot be extracted.")

                if pdf.page_count != document.page_count:
                    raise PdfExtractionError("PDF page count changed after ingestion.")

                extracted_pages = []

                for page_index, page in enumerate(pdf):
                    text = page.get_text("text")
                    meaningful_character_count = len(text.strip())

                    extracted_pages.append(
                        PageText(
                            page_number=page_index + 1,
                            text=text,
                            character_count=len(text),
                            requires_ocr=(meaningful_character_count < self.ocr_min_characters),
                            page_width=page.rect.width,
                            page_height=page.rect.height,
                            embedded_image_count=len(page.get_images(full=True)),
                            vector_drawing_count=len(page.get_drawings()),
                        )
                    )

                return ExtractedDocument(
                    source_path=document.file_path,
                    file_name=document.file_name,
                    page_count=pdf.page_count,
                    pages=tuple(extracted_pages),
                )

        except PdfExtractionError:
            raise

        except (
            OSError,
            pymupdf.FileDataError,
            pymupdf.EmptyFileError,
        ) as exc:
            raise PdfExtractionError(f"Unable to extract text from PDF: {path}") from exc
