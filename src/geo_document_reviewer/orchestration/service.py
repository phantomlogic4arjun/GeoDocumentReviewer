from pathlib import Path

from geo_document_reviewer.extraction.service import PdfExtractionService
from geo_document_reviewer.ingestion.service import PdfIngestionService
from geo_document_reviewer.ocr.service import OcrService
from geo_document_reviewer.orchestration.models import (
    ProcessedDocument,
    ProcessedPage,
)


class DocumentProcessingError(Exception):
    """Raised when the complete document processing workflow fails."""


class DocumentProcessingService:
    """Coordinates PDF ingestion, text extraction, and OCR processing."""

    def __init__(
        self,
        ingestion_service: PdfIngestionService | None = None,
        extraction_service: PdfExtractionService | None = None,
        ocr_service: OcrService | None = None,
    ) -> None:
        self.ingestion_service = (
            ingestion_service if ingestion_service is not None else PdfIngestionService()
        )
        self.extraction_service = (
            extraction_service if extraction_service is not None else PdfExtractionService()
        )
        self.ocr_service = ocr_service if ocr_service is not None else OcrService()

    def process(self, file_path: Path | str) -> ProcessedDocument:
        """Process a PDF and return its extracted and OCR-recognized content."""

        try:
            document = self.ingestion_service.ingest(file_path)

            extracted_document = self.extraction_service.extract(document)

            pages_requiring_ocr = extracted_document.pages_requiring_ocr

            ocr_results = (
                self.ocr_service.process_pages(
                    document,
                    list(pages_requiring_ocr),
                )
                if pages_requiring_ocr
                else ()
            )

            if len(ocr_results) != len(pages_requiring_ocr):
                raise ValueError("OCR must return exactly one result for every requested page.")

            ocr_results_by_page = {result.page_number: result for result in ocr_results}

            if set(ocr_results_by_page) != set(pages_requiring_ocr):
                raise ValueError("OCR results must match the requested page numbers exactly.")

            processed_pages = tuple(
                ProcessedPage(
                    page_number=page.page_number,
                    extracted_text=page.text,
                    requires_ocr=page.requires_ocr,
                    ocr_result=ocr_results_by_page.get(page.page_number),
                    page_width=page.page_width,
                    page_height=page.page_height,
                    embedded_image_count=page.embedded_image_count,
                    vector_drawing_count=page.vector_drawing_count,
                )
                for page in extracted_document.pages
            )

            return ProcessedDocument(
                source_path=extracted_document.source_path,
                file_name=extracted_document.file_name,
                page_count=extracted_document.page_count,
                pages=processed_pages,
            )

        except Exception as exc:
            raise DocumentProcessingError(f"Unable to process PDF document: {file_path}") from exc
