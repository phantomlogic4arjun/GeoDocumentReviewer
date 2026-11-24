import pytest
from pydantic import ValidationError

from geo_document_reviewer.rendering.models import RenderedPage


def create_rendered_page(**overrides) -> RenderedPage:
    data = {
        "page_number": 1,
        "image_bytes": b"sample-png-data",
        "image_format": "png",
        "pixel_width": 1191,
        "pixel_height": 1684,
        "page_width": 595.0,
        "page_height": 842.0,
        "dpi": 144,
    }
    data.update(overrides)
    return RenderedPage(**data)


def test_creates_rendered_page():
    page = create_rendered_page()

    assert page.page_number == 1
    assert page.image_bytes == b"sample-png-data"
    assert page.image_format == "png"
    assert page.pixel_width == 1191
    assert page.pixel_height == 1684
    assert page.page_width == 595.0
    assert page.page_height == 842.0
    assert page.dpi == 144


@pytest.mark.parametrize("page_number", [0, -1])
def test_rejects_invalid_page_number(page_number):
    with pytest.raises(ValidationError):
        create_rendered_page(page_number=page_number)


def test_rejects_empty_image_bytes():
    with pytest.raises(ValidationError):
        create_rendered_page(image_bytes=b"")


def test_rejects_invalid_image_format():
    with pytest.raises(ValidationError):
        create_rendered_page(image_format="jpeg")


@pytest.mark.parametrize(
    "field,value",
    [
        ("pixel_width", 0),
        ("pixel_height", -1),
        ("page_width", 0),
        ("page_height", -1),
        ("dpi", 0),
    ],
)
def test_rejects_invalid_dimensions_and_dpi(field, value):
    with pytest.raises(ValidationError):
        create_rendered_page(**{field: value})


def test_rendered_page_is_immutable():
    page = create_rendered_page()

    with pytest.raises(ValidationError):
        page.page_number = 2
