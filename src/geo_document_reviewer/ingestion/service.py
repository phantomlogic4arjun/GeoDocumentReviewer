from pathlib import Path

import pymupdf

from geo_document_reviewer.ingestion.models import PdfDocument


class PdfIngestionError(Exception):
    """Raised when a PDF cannot be ingested."""


class PdfIngestionService:
    """Validates PDF files and reads their basic document metadata."""

    def ingest(self, file_path: Path | str) -> PdfDocument:
        path = Path(file_path).expanduser()

        if not path.exists():
            raise PdfIngestionError(f"PDF file does not exist: {path}")

        if not path.is_file():
            raise PdfIngestionError(f"Path is not a file: {path}")

        if path.suffix.lower() != ".pdf":
            raise PdfIngestionError("File must have a .pdf extension.")

        try:
            file_size_bytes = path.stat().st_size

            if file_size_bytes == 0:
                raise PdfIngestionError("PDF file is empty.")

            with pymupdf.open(path) as pdf:
                if pdf.needs_pass:
                    raise PdfIngestionError(
                        "PDF is password-protected. Password support is not implemented yet."
                    )

                if pdf.page_count == 0:
                    raise PdfIngestionError("PDF contains no pages.")

                metadata = {
                    key: value
                    for key, value in pdf.metadata.items()
                    if isinstance(value, str) or value is None
                }

                return PdfDocument(
                    file_path=path.resolve(),
                    file_name=path.name,
                    file_size_bytes=file_size_bytes,
                    page_count=pdf.page_count,
                    metadata=metadata,
                )

        except PdfIngestionError:
            raise
        except (OSError, pymupdf.FileDataError, pymupdf.EmptyFileError) as exc:
            raise PdfIngestionError(f"Unable to read PDF file: {path}") from exc
