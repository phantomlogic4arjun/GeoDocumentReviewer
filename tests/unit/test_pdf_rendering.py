import pymupdf
import pytest

from geo_document_reviewer.ingestion.models import PdfDocument
from geo_document_reviewer.rendering.service import (
    PdfRenderingError,
    PdfRenderingService,
)


def create_pdf(tmp_path, page_count=2):
    pdf_path = tmp_path / "render_test.pdf"

    with pymupdf.open() as pdf:
        for page_number in range(page_count):
            page = pdf.new_page()
            page.insert_text(
                (72, 72),
                f"Rendering test page {page_number + 1}",
            )

        pdf.save(pdf_path)

    return PdfDocument(
        file_path=pdf_path,
        file_name=pdf_path.name,
        file_size_bytes=pdf_path.stat().st_size,
        page_count=page_count,
    )


def test_renders_selected_page(tmp_path):
    document = create_pdf(tmp_path)

    results = PdfRenderingService().render_pages(document, [1])

    assert len(results) == 1
    assert results[0].page_number == 1
    assert results[0].image_bytes.startswith(b"\x89PNG\r\n\x1a\n")


def test_renders_pages_in_requested_order(tmp_path):
    document = create_pdf(tmp_path)

    results = PdfRenderingService().render_pages(
        document,
        [2, 1],
    )

    assert tuple(page.page_number for page in results) == (2, 1)


def test_preserves_page_dimensions(tmp_path):
    document = create_pdf(tmp_path)

    result = PdfRenderingService().render_pages(
        document,
        [1],
    )[0]

    assert result.page_width == pytest.approx(595.0)
    assert result.page_height == pytest.approx(842.0)


def test_renders_at_configured_dpi(tmp_path):
    document = create_pdf(tmp_path)

    result = PdfRenderingService(dpi=144).render_pages(
        document,
        [1],
    )[0]

    assert result.dpi == 144
    assert result.pixel_width == 1190
    assert result.pixel_height == 1684


def test_rejects_invalid_dpi():
    with pytest.raises(ValueError):
        PdfRenderingService(dpi=0)


@pytest.mark.parametrize("page_numbers", [[], [1, 1], [0], [3], [-1]])
def test_rejects_invalid_page_selections(tmp_path, page_numbers):
    document = create_pdf(tmp_path)

    with pytest.raises(PdfRenderingError):
        PdfRenderingService().render_pages(
            document,
            page_numbers,
        )


def test_rejects_missing_pdf(tmp_path):
    document = create_pdf(tmp_path)
    missing_path = tmp_path / "missing.pdf"

    missing_document = document.model_copy(update={"file_path": missing_path})

    with pytest.raises(PdfRenderingError):
        PdfRenderingService().render_pages(
            missing_document,
            [1],
        )


def test_rejects_changed_page_count(tmp_path):
    document = create_pdf(tmp_path)

    changed_document = document.model_copy(update={"page_count": 3})

    with pytest.raises(PdfRenderingError):
        PdfRenderingService().render_pages(
            changed_document,
            [1],
        )


def test_rejects_password_protected_pdf(tmp_path):
    pdf_path = tmp_path / "protected.pdf"

    with pymupdf.open() as pdf:
        pdf.new_page()
        pdf.save(
            pdf_path,
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            owner_pw="owner",
            user_pw="user",
        )

    document = PdfDocument(
        file_path=pdf_path,
        file_name=pdf_path.name,
        file_size_bytes=pdf_path.stat().st_size,
        page_count=1,
    )

    with pytest.raises(PdfRenderingError):
        PdfRenderingService().render_pages(document, [1])
