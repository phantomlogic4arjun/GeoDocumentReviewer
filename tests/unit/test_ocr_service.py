from pathlib import Path
from unittest.mock import patch

import pymupdf
import pytest

from geo_document_reviewer.ingestion.service import PdfIngestionService
from geo_document_reviewer.ocr.models import OcrPageResult
from geo_document_reviewer.ocr.service import OcrService, OcrServiceError


@pytest.fixture
def create_pdf(tmp_path):
    def _create_pdf() -> Path:
        pdf_path = tmp_path / "ocr_test.pdf"

        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.insert_text((72, 72), "Borehole BH01")
            pdf.new_page()
            pdf.save(pdf_path)

        return pdf_path

    return _create_pdf


@pytest.fixture
def ingested_document(create_pdf):
    return PdfIngestionService().ingest(create_pdf())


def test_ocr_returns_page_result(ingested_document):
    service = OcrService()

    with patch.object(
        service,
        "_recognize_page",
        return_value=("Borehole BH01", 95.0),
    ):
        results = service.process_pages(ingested_document, [1])

    assert len(results) == 1
    assert isinstance(results[0], OcrPageResult)
    assert results[0].page_number == 1
    assert results[0].text == "Borehole BH01"
    assert results[0].confidence == 95.0


def test_processes_only_requested_pages(ingested_document):
    service = OcrService()

    with patch.object(
        service,
        "_recognize_page",
        return_value=("Recognized text", 90.0),
    ) as recognize:
        results = service.process_pages(ingested_document, [2])

    assert len(results) == 1
    assert results[0].page_number == 2
    recognize.assert_called_once()


def test_returns_results_in_requested_page_order(ingested_document):
    service = OcrService()

    with patch.object(
        service,
        "_recognize_page",
        side_effect=[
            ("Page two", 90.0),
            ("Page one", 95.0),
        ],
    ):
        results = service.process_pages(ingested_document, [2, 1])

    assert [result.page_number for result in results] == [2, 1]


def test_rejects_invalid_page_number(ingested_document):
    service = OcrService()

    with pytest.raises(OcrServiceError):
        service.process_pages(ingested_document, [3])


def test_rejects_duplicate_page_numbers(ingested_document):
    service = OcrService()

    with pytest.raises(OcrServiceError):
        service.process_pages(ingested_document, [1, 1])


def test_rejects_empty_page_list(ingested_document):
    service = OcrService()

    with pytest.raises(OcrServiceError):
        service.process_pages(ingested_document, [])


def test_rejects_non_positive_dpi():
    with pytest.raises(ValueError):
        OcrService(dpi=0)


def test_rejects_missing_pdf(ingested_document):
    service = OcrService()
    ingested_document.file_path.unlink()

    with pytest.raises(OcrServiceError):
        service.process_pages(ingested_document, [1])


def test_uses_configured_language(ingested_document):
    service = OcrService(language="eng")

    with patch.object(
        service,
        "_recognize_page",
        return_value=("Recognized text", 90.0),
    ):
        results = service.process_pages(ingested_document, [1])

    assert results[0].language == "eng"
