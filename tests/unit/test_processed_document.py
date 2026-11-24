from pathlib import Path

import pytest
from pydantic import ValidationError

from geo_document_reviewer.ocr.models import OcrPageResult
from geo_document_reviewer.orchestration.models import (
    ProcessedDocument,
    ProcessedPage,
)


def create_ocr_result(
    page_number: int = 1,
    text: str = "Recognized borehole information",
) -> OcrPageResult:
    return OcrPageResult(
        page_number=page_number,
        text=text,
        confidence=95.5,
        language="eng",
        dpi=300,
    )


def create_processed_page(
    page_number: int = 1,
    extracted_text: str = "Native PDF text",
    requires_ocr: bool = False,
    ocr_result: OcrPageResult | None = None,
) -> ProcessedPage:
    return ProcessedPage(
        page_number=page_number,
        extracted_text=extracted_text,
        requires_ocr=requires_ocr,
        ocr_result=ocr_result,
    )


def create_processed_document(
    pages: tuple[ProcessedPage, ...] | None = None,
) -> ProcessedDocument:
    if pages is None:
        pages = (
            create_processed_page(page_number=1),
            create_processed_page(page_number=2),
        )

    return ProcessedDocument(
        source_path=Path("report.pdf"),
        file_name="report.pdf",
        page_count=len(pages),
        pages=pages,
    )


def test_creates_processed_page():
    page = create_processed_page()

    assert page.page_number == 1
    assert page.extracted_text == "Native PDF text"
    assert page.requires_ocr is False
    assert page.ocr_result is None


def test_preserves_native_text_when_ocr_is_available():
    ocr_result = create_ocr_result()

    page = create_processed_page(
        extracted_text="Original extracted text",
        requires_ocr=True,
        ocr_result=ocr_result,
    )

    assert page.extracted_text == "Original extracted text"
    assert page.ocr_result.text == "Recognized borehole information"


def test_review_text_prefers_non_empty_ocr_text():
    page = create_processed_page(
        extracted_text="Native PDF text",
        requires_ocr=True,
        ocr_result=create_ocr_result(),
    )

    assert page.review_text == "Recognized borehole information"


def test_review_text_falls_back_to_native_text_when_ocr_is_empty():
    page = create_processed_page(
        extracted_text="Native PDF text",
        requires_ocr=True,
        ocr_result=create_ocr_result(text="   "),
    )

    assert page.review_text == "Native PDF text"


def test_review_text_uses_native_text_without_ocr():
    page = create_processed_page()

    assert page.review_text == "Native PDF text"


def test_rejects_ocr_result_for_different_page():
    with pytest.raises(ValidationError):
        create_processed_page(
            page_number=1,
            requires_ocr=True,
            ocr_result=create_ocr_result(page_number=2),
        )


def test_rejects_ocr_result_when_ocr_is_not_required():
    with pytest.raises(ValidationError):
        create_processed_page(
            requires_ocr=False,
            ocr_result=create_ocr_result(),
        )


def test_processed_page_is_immutable():
    page = create_processed_page()

    with pytest.raises(ValidationError):
        page.page_number = 2


def test_creates_processed_document():
    document = create_processed_document()

    assert document.file_name == "report.pdf"
    assert document.page_count == 2
    assert len(document.pages) == 2


def test_rejects_processed_document_page_count_mismatch():
    with pytest.raises(ValidationError):
        ProcessedDocument(
            source_path=Path("report.pdf"),
            file_name="report.pdf",
            page_count=3,
            pages=(create_processed_page(page_number=1),),
        )


def test_rejects_non_sequential_page_numbers():
    with pytest.raises(ValidationError):
        create_processed_document(
            pages=(
                create_processed_page(page_number=1),
                create_processed_page(page_number=3),
            )
        )


def test_identifies_pages_processed_with_ocr():
    document = create_processed_document(
        pages=(
            create_processed_page(
                page_number=1,
                requires_ocr=True,
                ocr_result=create_ocr_result(page_number=1),
            ),
            create_processed_page(page_number=2),
            create_processed_page(
                page_number=3,
                requires_ocr=True,
                ocr_result=create_ocr_result(page_number=3),
            ),
        )
    )

    assert document.pages_processed_with_ocr == (1, 3)


def test_returns_review_text_indexed_by_page_number():
    document = create_processed_document()

    assert document.review_text_by_page == {
        1: "Native PDF text",
        2: "Native PDF text",
    }


def test_processed_document_is_immutable():
    document = create_processed_document()

    with pytest.raises(ValidationError):
        document.page_count = 5
