from pathlib import Path
from unittest.mock import Mock

import pytest

from geo_document_reviewer.extraction.models import (
    ExtractedDocument,
    PageText,
)
from geo_document_reviewer.ingestion.models import PdfDocument
from geo_document_reviewer.ocr.models import OcrPageResult
from geo_document_reviewer.orchestration.models import ProcessedDocument
from geo_document_reviewer.orchestration.service import (
    DocumentProcessingError,
    DocumentProcessingService,
)


@pytest.fixture
def pdf_document():
    return PdfDocument(
        file_path=Path("report.pdf"),
        file_name="report.pdf",
        file_size_bytes=1024,
        page_count=3,
        metadata={},
    )


@pytest.fixture
def extracted_document():
    return ExtractedDocument(
        source_path=Path("report.pdf"),
        file_name="report.pdf",
        page_count=3,
        pages=(
            PageText(
                page_number=1,
                text="Page one native text",
                character_count=len("Page one native text"),
                requires_ocr=False,
            ),
            PageText(
                page_number=2,
                text="",
                character_count=0,
                requires_ocr=True,
            ),
            PageText(
                page_number=3,
                text="Page three native text",
                character_count=len("Page three native text"),
                requires_ocr=False,
            ),
        ),
    )


@pytest.fixture
def ocr_result():
    return OcrPageResult(
        page_number=2,
        text="Recognized borehole information",
        confidence=96.5,
        language="eng",
        dpi=300,
    )


@pytest.fixture
def processing_services():
    ingestion = Mock()
    extraction = Mock()
    ocr = Mock()

    service = DocumentProcessingService(
        ingestion_service=ingestion,
        extraction_service=extraction,
        ocr_service=ocr,
    )

    return service, ingestion, extraction, ocr


def test_processes_document_with_ocr(
    pdf_document,
    extracted_document,
    ocr_result,
    processing_services,
):
    service, ingestion, extraction, ocr = processing_services

    ingestion.ingest.return_value = pdf_document
    extraction.extract.return_value = extracted_document
    ocr.process_pages.return_value = (ocr_result,)

    result = service.process(Path("report.pdf"))

    assert isinstance(result, ProcessedDocument)
    assert result.file_name == "report.pdf"
    assert result.page_count == 3
    assert len(result.pages) == 3

    assert result.pages[0].review_text == "Page one native text"
    assert result.pages[1].review_text == "Recognized borehole information"
    assert result.pages[2].review_text == "Page three native text"

    assert result.pages_processed_with_ocr == (2,)

    ingestion.ingest.assert_called_once_with(Path("report.pdf"))
    extraction.extract.assert_called_once_with(pdf_document)
    ocr.process_pages.assert_called_once_with(pdf_document, [2])


def test_preserves_native_text_after_ocr(
    pdf_document,
    extracted_document,
    ocr_result,
    processing_services,
):
    service, ingestion, extraction, ocr = processing_services

    ingestion.ingest.return_value = pdf_document
    extraction.extract.return_value = extracted_document
    ocr.process_pages.return_value = (ocr_result,)

    result = service.process("report.pdf")

    assert result.pages[1].extracted_text == ""
    assert result.pages[1].ocr_result == ocr_result


def test_skips_ocr_when_no_pages_require_it(
    pdf_document,
    processing_services,
):
    service, ingestion, extraction, ocr = processing_services

    extracted = ExtractedDocument(
        source_path=Path("report.pdf"),
        file_name="report.pdf",
        page_count=3,
        pages=(
            PageText(
                page_number=1,
                text="Page one",
                character_count=8,
                requires_ocr=False,
            ),
            PageText(
                page_number=2,
                text="Page two",
                character_count=8,
                requires_ocr=False,
            ),
            PageText(
                page_number=3,
                text="Page three",
                character_count=10,
                requires_ocr=False,
            ),
        ),
    )

    ingestion.ingest.return_value = pdf_document
    extraction.extract.return_value = extracted

    result = service.process("report.pdf")

    assert result.pages_processed_with_ocr == ()
    assert result.pages[0].review_text == "Page one"
    ocr.process_pages.assert_not_called()


def test_rejects_missing_ocr_result(
    pdf_document,
    extracted_document,
    processing_services,
):
    service, ingestion, extraction, ocr = processing_services

    ingestion.ingest.return_value = pdf_document
    extraction.extract.return_value = extracted_document
    ocr.process_pages.return_value = ()

    with pytest.raises(DocumentProcessingError) as exc_info:
        service.process("report.pdf")

    assert isinstance(exc_info.value.__cause__, ValueError)
    assert "exactly one result" in str(exc_info.value.__cause__)


def test_rejects_unexpected_ocr_page(
    pdf_document,
    extracted_document,
    processing_services,
):
    service, ingestion, extraction, ocr = processing_services

    ingestion.ingest.return_value = pdf_document
    extraction.extract.return_value = extracted_document
    ocr.process_pages.return_value = (
        OcrPageResult(
            page_number=3,
            text="Unexpected page",
            confidence=90,
            language="eng",
            dpi=300,
        ),
    )

    with pytest.raises(DocumentProcessingError) as exc_info:
        service.process("report.pdf")

    assert isinstance(exc_info.value.__cause__, ValueError)
    assert "requested page numbers exactly" in str(exc_info.value.__cause__)


def test_wraps_ingestion_errors(processing_services):
    service, ingestion, extraction, ocr = processing_services

    ingestion.ingest.side_effect = OSError("Unable to read file")

    with pytest.raises(DocumentProcessingError) as exc_info:
        service.process("report.pdf")

    assert isinstance(exc_info.value.__cause__, OSError)
    extraction.extract.assert_not_called()
    ocr.process_pages.assert_not_called()


def test_wraps_extraction_errors(
    pdf_document,
    processing_services,
):
    service, ingestion, extraction, ocr = processing_services

    ingestion.ingest.return_value = pdf_document
    extraction.extract.side_effect = RuntimeError("Extraction failed")

    with pytest.raises(DocumentProcessingError) as exc_info:
        service.process("report.pdf")

    assert isinstance(exc_info.value.__cause__, RuntimeError)
    ocr.process_pages.assert_not_called()


def test_wraps_ocr_errors(
    pdf_document,
    extracted_document,
    processing_services,
):
    service, ingestion, extraction, ocr = processing_services

    ingestion.ingest.return_value = pdf_document
    extraction.extract.return_value = extracted_document
    ocr.process_pages.side_effect = RuntimeError("OCR failed")

    with pytest.raises(DocumentProcessingError) as exc_info:
        service.process("report.pdf")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_processes_all_pages_when_all_require_ocr(
    pdf_document,
    processing_services,
):
    service, ingestion, extraction, ocr = processing_services

    extracted = ExtractedDocument(
        source_path=Path("report.pdf"),
        file_name="report.pdf",
        page_count=3,
        pages=tuple(
            PageText(
                page_number=page_number,
                text="",
                character_count=0,
                requires_ocr=True,
            )
            for page_number in range(1, 4)
        ),
    )

    ocr_results = tuple(
        OcrPageResult(
            page_number=page_number,
            text=f"Recognized page {page_number}",
            confidence=95,
            language="eng",
            dpi=300,
        )
        for page_number in range(1, 4)
    )

    ingestion.ingest.return_value = pdf_document
    extraction.extract.return_value = extracted
    ocr.process_pages.return_value = ocr_results

    result = service.process("report.pdf")

    assert result.pages_processed_with_ocr == (1, 2, 3)
    ocr.process_pages.assert_called_once_with(
        pdf_document,
        [1, 2, 3],
    )
