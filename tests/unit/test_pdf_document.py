from pathlib import Path

import pytest
from pydantic import ValidationError

from geo_document_reviewer.ingestion.models import PdfDocument


def test_creates_pdf_document_with_valid_data():
    document = PdfDocument(
        file_path=Path("input/reports/sample.pdf"),
        file_name="sample.pdf",
        file_size_bytes=1024,
        page_count=50,
    )

    assert document.file_name == "sample.pdf"
    assert document.file_size_bytes == 1024
    assert document.page_count == 50
    assert document.metadata == {}


def test_converts_file_path_to_path_object():
    document = PdfDocument(
        file_path="input/reports/sample.pdf",
        file_name="sample.pdf",
        file_size_bytes=1024,
        page_count=50,
    )

    assert isinstance(document.file_path, Path)


def test_stores_pdf_metadata():
    document = PdfDocument(
        file_path=Path("sample.pdf"),
        file_name="sample.pdf",
        file_size_bytes=1024,
        page_count=10,
        metadata={
            "title": "Geotechnical Interpretative Report",
            "author": "Example Consultant",
        },
    )

    assert document.metadata["title"] == "Geotechnical Interpretative Report"
    assert document.metadata["author"] == "Example Consultant"


def test_rejects_empty_file_name():
    with pytest.raises(ValidationError):
        PdfDocument(
            file_path=Path("sample.pdf"),
            file_name="",
            file_size_bytes=1024,
            page_count=10,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("file_size_bytes", 0),
        ("file_size_bytes", -1),
        ("page_count", 0),
        ("page_count", -1),
    ],
)
def test_rejects_invalid_positive_values(field, value):
    data = {
        "file_path": Path("sample.pdf"),
        "file_name": "sample.pdf",
        "file_size_bytes": 1024,
        "page_count": 10,
    }
    data[field] = value

    with pytest.raises(ValidationError):
        PdfDocument(**data)


def test_document_is_immutable():
    document = PdfDocument(
        file_path=Path("sample.pdf"),
        file_name="sample.pdf",
        file_size_bytes=1024,
        page_count=10,
    )

    with pytest.raises(ValidationError):
        document.page_count = 20
