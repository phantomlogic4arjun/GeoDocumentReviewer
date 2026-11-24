from pathlib import Path

import pymupdf

from geo_document_reviewer.extraction.service import PdfExtractionService
from geo_document_reviewer.ingestion.service import PdfIngestionService
from geo_document_reviewer.ocr.service import OcrService


def test_tesseract_recognizes_text_inside_image_pdf(tmp_path: Path):
    source_pdf_path = tmp_path / "source.pdf"
    image_pdf_path = tmp_path / "scanned_report.pdf"

    # Create a PDF containing readable text.
    with pymupdf.open() as source_pdf:
        page = source_pdf.new_page(width=900, height=300)
        page.insert_text(
            (50, 150),
            "BOREHOLE BH01",
            fontname="hebo",
            fontsize=65,
        )
        source_pdf.save(source_pdf_path)

    # Render the text page as an image.
    with pymupdf.open(source_pdf_path) as source_pdf:
        pixmap = source_pdf[0].get_pixmap(
            matrix=pymupdf.Matrix(2, 2),
            alpha=False,
        )
        image_bytes = pixmap.tobytes("png")

    # Create a new PDF containing only the rendered image.
    with pymupdf.open() as image_pdf:
        page = image_pdf.new_page(width=900, height=300)
        page.insert_image(page.rect, stream=image_bytes)
        image_pdf.save(image_pdf_path)

    document = PdfIngestionService().ingest(image_pdf_path)

    # Normal PDF text extraction should find no selectable text.
    extracted = PdfExtractionService().extract(document)

    assert extracted.pages[0].text.strip() == ""
    assert extracted.pages_requiring_ocr == (1,)

    # Run actual Tesseract OCR.
    results = OcrService(dpi=300).process_pages(document, [1])

    assert len(results) == 1
    assert "BOREHOLE" in results[0].text.upper()
    assert results[0].confidence > 0
