from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RenderedPage(BaseModel):
    """Rendered image and metadata for an individual PDF page."""

    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)

    image_bytes: bytes = Field(min_length=1)
    image_format: Literal["png"] = "png"

    pixel_width: int = Field(gt=0)
    pixel_height: int = Field(gt=0)

    page_width: float = Field(gt=0)
    page_height: float = Field(gt=0)

    dpi: int = Field(gt=0)
