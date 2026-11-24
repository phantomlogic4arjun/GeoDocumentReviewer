from io import BytesIO
from pathlib import Path

import pytesseract
from PIL import Image
from pytesseract import Output

from geo_document_reviewer.config.settings import settings
from geo_document_reviewer.ingestion.models import PdfDocument
from geo_document_reviewer.ocr.models import OcrPageResult
from geo_document_reviewer.rendering.models import RenderedPage
from geo_document_reviewer.rendering.service import (
    PdfRenderingError,
    PdfRenderingService,
)


class OcrServiceError(Exception):
    """Raised when OCR processing cannot be completed."""


class OcrService:
    """Recognizes text from selected PDF pages using local Tesseract OCR."""

    def __init__(
        self,
        language: str | None = None,
        dpi: int | None = None,
        tesseract_cmd: str | Path | None = None,
        rendering_service: PdfRenderingService | None = None,
    ) -> None:
        self.language = language if language is not None else settings.ocr_language
        self.dpi = dpi if dpi is not None else settings.ocr_dpi
        executable = tesseract_cmd if tesseract_cmd is not None else settings.tesseract_cmd

        if not self.language.strip():
            raise ValueError("language cannot be empty.")

        if self.dpi < 1:
            raise ValueError("dpi must be greater than zero.")

        self.rendering_service = (
            rendering_service
            if rendering_service is not None
            else PdfRenderingService(dpi=self.dpi)
        )

        if executable:
            pytesseract.pytesseract.tesseract_cmd = str(executable)

    def process_pages(
        self,
        document: PdfDocument,
        page_numbers: list[int],
    ) -> tuple[OcrPageResult, ...]:
        """Run OCR on selected pages and return their recognized text."""
        try:
            rendered_pages = self.rendering_service.render_pages(
                document,
                page_numbers,
            )

            results = []

            for rendered_page in rendered_pages:
                text, confidence = self._recognize_page(rendered_page)

                results.append(
                    OcrPageResult(
                        page_number=rendered_page.page_number,
                        text=text,
                        confidence=confidence,
                        language=self.language,
                        dpi=rendered_page.dpi,
                    )
                )

            return tuple(results)

        except PdfRenderingError as exc:
            raise OcrServiceError(f"Unable to render PDF for OCR: {document.file_path}") from exc

        except (
            OSError,
            pytesseract.TesseractNotFoundError,
            pytesseract.TesseractError,
        ) as exc:
            raise OcrServiceError(f"Unable to perform OCR on PDF: {document.file_path}") from exc

    def _recognize_page(
        self,
        rendered_page: RenderedPage,
    ) -> tuple[str, float]:
        """Recognize text from an already rendered PNG page."""
        with Image.open(BytesIO(rendered_page.image_bytes)) as image:
            recognized_text = pytesseract.image_to_string(
                image,
                lang=self.language,
            )

            ocr_data = pytesseract.image_to_data(
                image,
                lang=self.language,
                output_type=Output.DICT,
            )

        valid_confidences = [
            float(confidence)
            for text, confidence in zip(
                ocr_data["text"],
                ocr_data["conf"],
                strict=True,
            )
            if text.strip() and float(confidence) >= 0
        ]

        average_confidence = (
            sum(valid_confidences) / len(valid_confidences) if valid_confidences else 0.0
        )

        return recognized_text, average_confidence
