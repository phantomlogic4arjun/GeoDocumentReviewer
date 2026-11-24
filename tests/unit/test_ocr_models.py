import pytest
from pydantic import ValidationError

from geo_document_reviewer.ocr.models import OcrPageResult


def test_creates_valid_ocr_result():
    result = OcrPageResult(
        page_number=1,
        text="Borehole BH01 encountered dense sand.",
        confidence=94.5,
        language="eng",
        dpi=300,
    )

    assert result.page_number == 1
    assert result.text == "Borehole BH01 encountered dense sand."
    assert result.confidence == 94.5
    assert result.language == "eng"
    assert result.dpi == 300


def test_rejects_page_number_below_one():
    with pytest.raises(ValidationError):
        OcrPageResult(
            page_number=0,
            text="Recognized text",
            confidence=90,
            language="eng",
            dpi=300,
        )


@pytest.mark.parametrize("confidence", [-1, 101])
def test_rejects_invalid_confidence(confidence):
    with pytest.raises(ValidationError):
        OcrPageResult(
            page_number=1,
            text="Recognized text",
            confidence=confidence,
            language="eng",
            dpi=300,
        )


def test_allows_zero_confidence():
    result = OcrPageResult(
        page_number=1,
        text="",
        confidence=0,
        language="eng",
        dpi=300,
    )

    assert result.confidence == 0


def test_rejects_empty_language():
    with pytest.raises(ValidationError):
        OcrPageResult(
            page_number=1,
            text="Recognized text",
            confidence=90,
            language="",
            dpi=300,
        )


def test_rejects_invalid_dpi():
    with pytest.raises(ValidationError):
        OcrPageResult(
            page_number=1,
            text="Recognized text",
            confidence=90,
            language="eng",
            dpi=0,
        )


def test_ocr_result_is_immutable():
    result = OcrPageResult(
        page_number=1,
        text="Recognized text",
        confidence=90,
        language="eng",
        dpi=300,
    )

    with pytest.raises(ValidationError):
        result.text = "Modified text"
