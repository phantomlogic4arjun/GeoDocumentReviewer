from datetime import date
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from geo_document_reviewer.comments.service import accepted_comments
from geo_document_reviewer.review.models import (
    ReviewAssessment,
    ReviewerDecisionRecord,
)

HEADERS = [
    "Comment ID",
    "Document Number",
    "Revision",
    "Section / Sheet Ref",
    "Comment",
    "Category",
    "Criticality",
    "Raised By",
    "Date Raised",
    "Author Response",
    "Response Code",
    "Status",
    "Closed By / Date",
]


class CrsExcelService:
    """Creates a CRS workbook from engineer-approved comments."""

    def export(
        self,
        assessment: ReviewAssessment,
        decisions: dict[str, ReviewerDecisionRecord],
        document_number: str,
        revision: str,
        raised_by: str,
    ) -> bytes:
        approved = accepted_comments(assessment, decisions)

        workbook = Workbook()
        ws = workbook.active
        ws.title = "CRS"
        ws.append(HEADERS)

        for index, (finding, reviewer_decision) in enumerate(approved, start=1):
            references = ", ".join(
                f"PDF p. {e.pdf_page}" + (f" — {e.section}" if e.section else "")
                for e in finding.supporting_evidence
            )

            ws.append(
                [
                    f"CR-{index:03d}",
                    document_number,
                    revision,
                    references,
                    reviewer_decision.final_comment,
                    finding.category.value,
                    finding.criticality.value,
                    raised_by,
                    date.today().isoformat(),
                    None,
                    None,
                    "Open",
                    None,
                ]
            )

        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F4E78")
            cell.alignment = Alignment(wrap_text=True, vertical="center")

        widths = [14, 20, 12, 35, 65, 18, 15, 20, 15, 40, 16, 14, 22]
        for index, width in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(index)].width = width

        ws.row_dimensions[1].height = 32
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")

        status = workbook.create_sheet("Status Codes")
        status.append(["Status", "Description"])
        status.append(["Open", "Awaiting author response"])
        status.append(["In Progress", "Response or action underway"])
        status.append(["Closed", "Reviewed and closed by the responsible reviewer"])

        instructions = workbook.create_sheet("How To Use")
        instructions.append(["PMEC Comment Resolution Sheet"])
        instructions.append(["One comment per row."])
        instructions.append(["Only the responsible reviewer should close a comment."])
        instructions.append(["AI-generated findings are not automatically approved."])
        instructions.append(["Only accepted reviewer comments are exported."])
        instructions.column_dimensions["A"].width = 100

        output = BytesIO()
        workbook.save(output)
        return output.getvalue()
