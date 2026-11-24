import pymupdf
import pytest

from geo_document_reviewer.ingestion.service import (
    PdfIngestionError,
    PdfIngestionService,
)


@pytest.fixture
def service():
    return PdfIngestionService()


@pytest.fixture
def valid_pdf(tmp_path):
    pdf_path = tmp_path / "sample.pdf"

    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Sample geotechnical report")
        document.save(pdf_path)

    return pdf_path


def test_ingests_valid_pdf(service, valid_pdf):
    document = service.ingest(valid_pdf)

    assert document.file_name == "sample.pdf"
    assert document.file_size_bytes > 0
    assert document.page_count == 1
    assert document.file_path == valid_pdf.resolve()


def test_extracts_pdf_metadata(service, tmp_path):
    pdf_path = tmp_path / "metadata.pdf"

    with pymupdf.open() as document:
        document.new_page()
        document.set_metadata({"title": "Geotechnical Report"})
        document.save(pdf_path)

    result = service.ingest(pdf_path)

    assert result.metadata["title"] == "Geotechnical Report"


def test_rejects_missing_file(service, tmp_path):
    with pytest.raises(PdfIngestionError, match="does not exist"):
        service.ingest(tmp_path / "missing.pdf")


def test_rejects_directory(service, tmp_path):
    with pytest.raises(PdfIngestionError, match="not a file"):
        service.ingest(tmp_path)


def test_rejects_non_pdf_extension(service, tmp_path):
    file_path = tmp_path / "report.txt"
    file_path.write_text("Not a PDF", encoding="utf-8")

    with pytest.raises(PdfIngestionError, match="extension"):
        service.ingest(file_path)


def test_rejects_empty_file(service, tmp_path):
    pdf_path = tmp_path / "empty.pdf"
    pdf_path.touch()

    with pytest.raises(PdfIngestionError, match="empty"):
        service.ingest(pdf_path)


def test_rejects_corrupt_pdf(service, tmp_path):
    pdf_path = tmp_path / "corrupt.pdf"
    pdf_path.write_bytes(b"This is not a valid PDF")

    with pytest.raises(PdfIngestionError, match="Unable to read PDF"):
        service.ingest(pdf_path)


def test_rejects_password_protected_pdf(service, tmp_path):
    pdf_path = tmp_path / "protected.pdf"

    with pymupdf.open() as document:
        document.new_page()
        document.save(
            pdf_path,
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            owner_pw="owner-password",
            user_pw="user-password",
        )

    with pytest.raises(PdfIngestionError, match="password-protected"):
        service.ingest(pdf_path)
