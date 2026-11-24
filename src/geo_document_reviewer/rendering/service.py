import pymupdf

from geo_document_reviewer.ingestion.models import PdfDocument
from geo_document_reviewer.rendering.models import RenderedPage


class PdfRenderingError(Exception):
    """Raised when PDF pages cannot be rendered."""


class PdfRenderingService:
    """Renders selected PDF pages into PNG images."""

    def __init__(self, dpi: int = 150) -> None:
        if not isinstance(dpi, int) or isinstance(dpi, bool) or dpi < 1:
            raise ValueError("dpi must be a positive integer.")

        self.dpi = dpi

    def render_pages(
        self,
        document: PdfDocument,
        page_numbers: list[int],
    ) -> tuple[RenderedPage, ...]:
        """Render selected pages and return their image data."""

        if not page_numbers:
            raise PdfRenderingError("At least one page number must be provided.")

        if len(page_numbers) != len(set(page_numbers)):
            raise PdfRenderingError("Duplicate page numbers are not allowed.")

        if any(
            not isinstance(number, int)
            or isinstance(number, bool)
            or number < 1
            or number > document.page_count
            for number in page_numbers
        ):
            raise PdfRenderingError(
                "Requested page numbers must be within the document page range."
            )

        path = document.file_path

        if not path.exists() or not path.is_file():
            raise PdfRenderingError(f"Source PDF is unavailable: {path}")

        try:
            with pymupdf.open(path) as pdf:
                if pdf.needs_pass:
                    raise PdfRenderingError("PDF is password-protected and cannot be rendered.")

                if pdf.page_count != document.page_count:
                    raise PdfRenderingError("PDF page count changed after ingestion.")

                results = []

                scale = self.dpi / 72
                matrix = pymupdf.Matrix(scale, scale)

                for page_number in page_numbers:
                    page = pdf.load_page(page_number - 1)

                    pixmap = page.get_pixmap(
                        matrix=matrix,
                        alpha=False,
                    )

                    results.append(
                        RenderedPage(
                            page_number=page_number,
                            image_bytes=pixmap.tobytes("png"),
                            image_format="png",
                            pixel_width=pixmap.width,
                            pixel_height=pixmap.height,
                            page_width=page.rect.width,
                            page_height=page.rect.height,
                            dpi=self.dpi,
                        )
                    )

                return tuple(results)

        except PdfRenderingError:
            raise

        except (
            OSError,
            pymupdf.FileDataError,
            pymupdf.EmptyFileError,
        ) as exc:
            raise PdfRenderingError(f"Unable to render PDF: {path}") from exc
