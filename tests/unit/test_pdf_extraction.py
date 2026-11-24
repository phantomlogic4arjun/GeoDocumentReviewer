from pathlib import Path

import pymupdf
import pytest

from geo_document_reviewer.extraction.models import (
    ExtractedDocument,
)
from geo_document_reviewer.extraction.service import (
    PdfExtractionError,
    PdfExtractionService,
)
from geo_document_reviewer.ingestion.service import PdfIngestionService


@pytest.fixture
def extraction_service():
    return PdfExtractionService()


@pytest.fixture
def create_pdf(tmp_path):
    def _create_pdf(pages: list[str]) -> Path:
        pdf_path = tmp_path / "test_report.pdf"

        with pymupdf.open() as pdf:
            for page_text in pages:
                page = pdf.new_page()

                if page_text:
                    page.insert_text((72, 72), page_text)

            pdf.save(pdf_path)

        return pdf_path

    return _create_pdf


@pytest.fixture
def create_visual_pdf(tmp_path):
    def _create_visual_pdf() -> Path:
        pdf_path = tmp_path / "visual_report.pdf"

        with pymupdf.open() as pdf:
            page = pdf.new_page(width=842, height=595)

            page.insert_text(
                (72, 72),
                "Geotechnical site investigation drawing",
            )

            # Add vector content.
            page.draw_rect(
                pymupdf.Rect(100, 100, 300, 200),
                color=(0, 0, 1),
                width=2,
            )

            # Add an embedded raster image.
            image = pymupdf.Pixmap(
                pymupdf.csRGB,
                pymupdf.IRect(0, 0, 100, 100),
                0,
            )
            image.clear_with(255)

            page.insert_image(
                pymupdf.Rect(350, 100, 450, 200),
                pixmap=image,
            )

            pdf.save(pdf_path)

        return pdf_path

    return _create_visual_pdf


def test_extracts_text_from_all_pages(extraction_service, create_pdf):
    pdf_path = create_pdf(
        [
            "Geotechnical investigation findings",
            "Foundation recommendations and design parameters",
        ]
    )
    document = PdfIngestionService().ingest(pdf_path)

    result = extraction_service.extract(document)

    assert isinstance(result, ExtractedDocument)
    assert result.page_count == 2
    assert result.pages[0].page_number == 1
    assert result.pages[1].page_number == 2
    assert "Geotechnical investigation findings" in result.pages[0].text
    assert "Foundation recommendations" in result.pages[1].text


def test_records_correct_character_counts(extraction_service, create_pdf):
    pdf_path = create_pdf(["Geotechnical investigation findings"])
    document = PdfIngestionService().ingest(pdf_path)

    result = extraction_service.extract(document)

    for page in result.pages:
        assert page.character_count == len(page.text)


def test_flags_blank_page_as_ocr_candidate(extraction_service, create_pdf):
    pdf_path = create_pdf(["", "Geotechnical investigation findings"])
    document = PdfIngestionService().ingest(pdf_path)

    result = extraction_service.extract(document)

    assert result.pages[0].requires_ocr is True
    assert result.pages[1].requires_ocr is False


def test_flags_sparse_text_page_as_ocr_candidate(create_pdf):
    service = PdfExtractionService(ocr_min_characters=20)
    pdf_path = create_pdf(["Short text"])
    document = PdfIngestionService().ingest(pdf_path)

    result = service.extract(document)

    assert result.pages[0].requires_ocr is True


def test_allows_custom_ocr_threshold(create_pdf):
    service = PdfExtractionService(ocr_min_characters=5)
    pdf_path = create_pdf(["Short text"])
    document = PdfIngestionService().ingest(pdf_path)

    result = service.extract(document)

    assert result.pages[0].requires_ocr is False


def test_returns_source_metadata(extraction_service, create_pdf):
    pdf_path = create_pdf(["Geotechnical investigation findings"])
    document = PdfIngestionService().ingest(pdf_path)

    result = extraction_service.extract(document)

    assert result.source_path == document.file_path
    assert result.file_name == document.file_name
    assert result.page_count == document.page_count


def test_rejects_non_positive_ocr_threshold():
    with pytest.raises(ValueError):
        PdfExtractionService(ocr_min_characters=0)


def test_raises_error_when_source_file_is_missing(extraction_service, create_pdf):
    pdf_path = create_pdf(["Geotechnical investigation findings"])
    document = PdfIngestionService().ingest(pdf_path)
    pdf_path.unlink()

    with pytest.raises(PdfExtractionError):
        extraction_service.extract(document)


def test_rejects_page_count_change_after_ingestion(extraction_service, create_pdf, tmp_path):
    pdf_path = create_pdf(["Geotechnical investigation findings"])
    document = PdfIngestionService().ingest(pdf_path)

    replacement_path = tmp_path / "replacement.pdf"
    with pymupdf.open() as pdf:
        pdf.new_page()
        pdf.new_page()
        pdf.save(replacement_path)

    replacement_path.replace(pdf_path)

    with pytest.raises(PdfExtractionError):
        extraction_service.extract(document)


def test_extracts_page_dimensions(create_visual_pdf):
    pdf_path = create_visual_pdf()
    document = PdfIngestionService().ingest(pdf_path)

    result = PdfExtractionService().extract(document)
    page = result.pages[0]

    assert page.page_width == pytest.approx(842)
    assert page.page_height == pytest.approx(595)


def test_extracts_embedded_image_count(create_visual_pdf):
    pdf_path = create_visual_pdf()
    document = PdfIngestionService().ingest(pdf_path)

    result = PdfExtractionService().extract(document)

    assert result.pages[0].embedded_image_count == 1


def test_extracts_vector_drawing_count(create_visual_pdf):
    pdf_path = create_visual_pdf()
    document = PdfIngestionService().ingest(pdf_path)

    result = PdfExtractionService().extract(document)

    assert result.pages[0].vector_drawing_count > 0


def test_extracts_landscape_page_orientation(create_visual_pdf):
    pdf_path = create_visual_pdf()
    document = PdfIngestionService().ingest(pdf_path)

    result = PdfExtractionService().extract(document)

    assert result.pages[0].is_landscape is True
