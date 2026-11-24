from pathlib import Path

import pytest
from pydantic import ValidationError

from geo_document_reviewer.extraction.models import (
    ExtractedDocument,
    PageText,
)


def test_creates_page_text():
    page = PageText(
        page_number=1,
        text="Geotechnical investigation findings",
        character_count=35,
    )

    assert page.page_number == 1
    assert page.text == "Geotechnical investigation findings"
    assert page.character_count == 35
    assert page.requires_ocr is False


def test_rejects_page_number_below_one():
    with pytest.raises(ValidationError):
        PageText(
            page_number=0,
            text="Sample",
            character_count=6,
        )


def test_rejects_negative_character_count():
    with pytest.raises(ValidationError):
        PageText(
            page_number=1,
            text="Sample",
            character_count=-1,
        )


def test_page_text_is_immutable():
    page = PageText(
        page_number=1,
        text="Sample",
        character_count=6,
    )

    with pytest.raises(ValidationError):
        page.text = "Changed"


def test_creates_extracted_document():
    pages = (
        PageText(
            page_number=1,
            text="Introduction",
            character_count=12,
        ),
        PageText(
            page_number=2,
            text="Site investigation",
            character_count=18,
        ),
    )

    document = ExtractedDocument(
        source_path=Path("sample.pdf"),
        file_name="sample.pdf",
        page_count=2,
        pages=pages,
    )

    assert document.file_name == "sample.pdf"
    assert document.page_count == 2
    assert len(document.pages) == 2


def test_identifies_pages_requiring_ocr():
    pages = (
        PageText(
            page_number=1,
            text="Introduction",
            character_count=12,
        ),
        PageText(
            page_number=2,
            text="",
            character_count=0,
            requires_ocr=True,
        ),
        PageText(
            page_number=3,
            text="Conclusion",
            character_count=10,
        ),
    )

    document = ExtractedDocument(
        source_path=Path("sample.pdf"),
        file_name="sample.pdf",
        page_count=3,
        pages=pages,
    )

    assert document.pages_requiring_ocr == (2,)


def test_pages_requiring_ocr_is_empty_when_no_pages_are_flagged():
    document = ExtractedDocument(
        source_path=Path("sample.pdf"),
        file_name="sample.pdf",
        page_count=1,
        pages=(
            PageText(
                page_number=1,
                text="Introduction",
                character_count=12,
            ),
        ),
    )

    assert document.pages_requiring_ocr == ()


def test_extracted_document_is_immutable():
    document = ExtractedDocument(
        source_path=Path("sample.pdf"),
        file_name="sample.pdf",
        page_count=1,
        pages=(
            PageText(
                page_number=1,
                text="Introduction",
                character_count=12,
            ),
        ),
    )

    with pytest.raises(ValidationError):
        document.page_count = 2


def test_rejects_incorrect_character_count():
    with pytest.raises(ValidationError, match="character_count"):
        PageText(
            page_number=1,
            text="Introduction",
            character_count=10,
        )


def test_rejects_page_count_mismatch():
    with pytest.raises(ValidationError, match="page_count"):
        ExtractedDocument(
            source_path=Path("sample.pdf"),
            file_name="sample.pdf",
            page_count=2,
            pages=(
                PageText(
                    page_number=1,
                    text="Introduction",
                    character_count=12,
                ),
            ),
        )


def test_rejects_non_sequential_page_numbers():
    with pytest.raises(ValidationError, match="sequential"):
        ExtractedDocument(
            source_path=Path("sample.pdf"),
            file_name="sample.pdf",
            page_count=2,
            pages=(
                PageText(
                    page_number=1,
                    text="Introduction",
                    character_count=12,
                ),
                PageText(
                    page_number=3,
                    text="Conclusion",
                    character_count=10,
                ),
            ),
        )


def test_preserves_page_visual_metadata():
    page = PageText(
        page_number=1,
        text="Geotechnical investigation findings",
        character_count=35,
        page_width=595.0,
        page_height=842.0,
        embedded_image_count=2,
        vector_drawing_count=15,
    )

    assert page.page_width == 595.0
    assert page.page_height == 842.0
    assert page.embedded_image_count == 2
    assert page.vector_drawing_count == 15


def test_identifies_page_with_embedded_images():
    page = PageText(
        page_number=1,
        text="Site plan",
        character_count=9,
        embedded_image_count=1,
    )

    assert page.has_visual_content is True


def test_identifies_page_with_vector_drawings():
    page = PageText(
        page_number=1,
        text="Borehole log",
        character_count=12,
        vector_drawing_count=10,
    )

    assert page.has_visual_content is True


def test_identifies_page_without_visual_content():
    page = PageText(
        page_number=1,
        text="Introduction",
        character_count=12,
    )

    assert page.has_visual_content is False


def test_identifies_landscape_page():
    page = PageText(
        page_number=1,
        text="Geotechnical drawing",
        character_count=20,
        page_width=1191.0,
        page_height=843.0,
    )

    assert page.is_landscape is True


def test_identifies_portrait_page():
    page = PageText(
        page_number=1,
        text="Introduction",
        character_count=12,
        page_width=595.0,
        page_height=842.0,
    )

    assert page.is_landscape is False


def test_landscape_detection_returns_none_without_dimensions():
    page = PageText(
        page_number=1,
        text="Introduction",
        character_count=12,
    )

    assert page.is_landscape is None


def test_rejects_negative_visual_metadata():
    with pytest.raises(ValidationError):
        PageText(
            page_number=1,
            text="Sample",
            character_count=6,
            embedded_image_count=-1,
        )
