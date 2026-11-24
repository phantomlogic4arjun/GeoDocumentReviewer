from io import BytesIO

import streamlit as st

from geo_document_reviewer.comments.service import accepted_comments
from geo_document_reviewer.excel.service import CrsExcelService
from geo_document_reviewer.orchestration.service import DocumentProcessingService
from geo_document_reviewer.review.models import (
    ReviewDecision,
    ReviewerDecisionRecord,
    ReviewerStatus,
)
from geo_document_reviewer.review.service import ReviewService, ReviewServiceError

st.set_page_config(
    page_title="GeoDocumentReviewer",
    page_icon="📐",
    layout="wide",
)

st.title("GeoDocumentReviewer")
st.caption("AI-assisted geotechnical report review and CRS generation")

st.warning(
    "AI findings are suggestions, not engineering approvals. "
    "Only comments explicitly accepted by the reviewer are exported."
)

with st.sidebar:
    st.header("Review configuration")
    document_number = st.text_input("Document number", value="May Road GIR")
    revision = st.text_input("Revision", value="0")
    reviewer = st.text_input("Reviewer name")
    topics = st.multiselect(
        "Review topics",
        ["Settlement", "Groundwater"],
        default=["Settlement", "Groundwater"],
    )

uploaded_file = st.file_uploader("Upload a geotechnical PDF", type=["pdf"])

if uploaded_file is not None:
    st.write(f"**Selected report:** {uploaded_file.name}")
    st.write(f"**File size:** {uploaded_file.size / (1024 * 1024):.2f} MB")

    if st.button("Process PDF and run AI review", type="primary"):
        if not topics:
            st.error("Select at least one review topic.")
        else:
            try:
                with st.spinner("Processing PDF locally..."):
                    import tempfile
                    from pathlib import Path

                    with tempfile.TemporaryDirectory() as temp_dir:
                        pdf_path = Path(temp_dir) / uploaded_file.name
                        pdf_path.write_bytes(uploaded_file.getvalue())

                        processed = DocumentProcessingService().process(pdf_path)

                        st.session_state["processed_page_count"] = processed.page_count
                        st.session_state["processed_file"] = uploaded_file.name

                        with st.spinner("Sending report text to Qwen for review..."):
                            assessment, usage = ReviewService().review(
                                processed,
                                topics,
                            )

                st.session_state["assessment"] = assessment
                st.session_state["usage"] = usage
                st.session_state["decisions"] = {}
                st.success("Review completed.")

            except (ValueError, RuntimeError, ReviewServiceError) as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Processing failed: {exc}")

assessment = st.session_state.get("assessment")

if assessment:
    usage = st.session_state.get("usage", {})

    st.divider()
    st.subheader("Document processing")
    col1, col2, col3 = st.columns(3)
    col1.metric("PDF pages", assessment.page_count)
    col2.metric("Review findings", len(assessment.findings))
    col3.metric("Model cost", f"${usage.get('cost', 0):.6f}")

    st.caption(
        f"Model: {assessment.model_name} | "
        f"Input tokens: {usage.get('prompt_tokens', 'N/A')} | "
        f"Output tokens: {usage.get('completion_tokens', 'N/A')}"
    )

    st.subheader("Engineering review findings")
    decisions = st.session_state.setdefault("decisions", {})

    for finding in assessment.findings:
        with st.expander(
            f"{finding.topic} — {finding.decision.value} ({finding.confidence.value} confidence)",
            expanded=True,
        ):
            st.write("**AI reasoning**")
            st.write(finding.reasoning)

            if finding.supporting_evidence:
                st.write("**Supporting evidence**")
                for evidence in finding.supporting_evidence:
                    st.markdown(
                        f"- **PDF page {evidence.pdf_page}**"
                        + (f" — {evidence.section}" if evidence.section else "")
                        + f": {evidence.observation}"
                    )

            if finding.information_gaps:
                st.write("**Information gaps**")
                for gap in finding.information_gaps:
                    st.write(f"- {gap}")

            if finding.decision == ReviewDecision.COMMENT_REQUIRED:
                st.write("**Proposed comment**")
                comment_key = f"comment_{finding.finding_id}"
                existing = decisions.get(finding.finding_id)
                default_comment = (
                    existing.final_comment
                    if existing and existing.final_comment
                    else finding.proposed_comment or ""
                )
                edited_comment = st.text_area(
                    "Edit the proposed comment",
                    value=default_comment,
                    key=comment_key,
                )

                status_key = f"status_{finding.finding_id}"
                current_status = existing.status.value if existing else ReviewerStatus.PENDING.value
                selected_status = st.selectbox(
                    "Reviewer decision",
                    [item.value for item in ReviewerStatus],
                    index=[item.value for item in ReviewerStatus].index(current_status),
                    key=status_key,
                )

                notes = st.text_input(
                    "Reviewer notes",
                    value=existing.reviewer_notes or "" if existing else "",
                    key=f"notes_{finding.finding_id}",
                )

                if selected_status == ReviewerStatus.ACCEPTED.value:
                    if edited_comment.strip():
                        decisions[finding.finding_id] = ReviewerDecisionRecord(
                            finding_id=finding.finding_id,
                            status=ReviewerStatus.ACCEPTED,
                            final_comment=edited_comment.strip(),
                            reviewer_notes=notes or None,
                        )
                    else:
                        st.warning("An accepted comment cannot be empty.")
                        decisions.pop(finding.finding_id, None)

                elif selected_status == ReviewerStatus.REJECTED.value:
                    decisions[finding.finding_id] = ReviewerDecisionRecord(
                        finding_id=finding.finding_id,
                        status=ReviewerStatus.REJECTED,
                        reviewer_notes=notes or None,
                    )
                else:
                    decisions.pop(finding.finding_id, None)

            else:
                st.info(
                    "No proposed comment is available for this assessment. "
                    "You can add a manual engineering comment below."
                )

    st.divider()
    st.subheader("Add a manual engineering comment")

    with st.form("manual_comment_form"):
        manual_topic = st.selectbox(
            "Topic",
            ["Settlement", "Groundwater", "Other"],
        )
        manual_page = st.number_input(
            "Supporting PDF page",
            min_value=1,
            max_value=assessment.page_count,
            value=1,
        )
        manual_section = st.text_input("Section reference")
        manual_comment = st.text_area("Engineering comment")
        manual_category = st.selectbox(
            "Category",
            ["Technical", "Editorial", "Clarification"],
        )
        manual_criticality = st.selectbox(
            "Criticality",
            ["High", "Medium", "Low"],
        )
        add_manual = st.form_submit_button("Add approved manual comment")

    if add_manual:
        if manual_comment.strip():
            from uuid import uuid4

            decisions[f"manual_{uuid4()}"] = {
                "topic": manual_topic,
                "page": int(manual_page),
                "section": manual_section,
                "comment": manual_comment.strip(),
                "category": manual_category,
                "criticality": manual_criticality,
            }
            st.success("Manual comment added.")
        else:
            st.error("Enter a comment first.")

    approved_ai = accepted_comments(
        assessment,
        {
            key: value
            for key, value in decisions.items()
            if isinstance(value, ReviewerDecisionRecord)
        },
    )
    manual_comments = [value for value in decisions.values() if isinstance(value, dict)]

    st.divider()
    st.subheader("CRS export")
    st.metric(
        "Approved comments",
        len(approved_ai) + len(manual_comments),
    )

    if st.button("Generate CRS Excel"):
        try:
            from openpyxl import load_workbook

            # Generate the CRS workbook from approved AI findings.
            exporter = CrsExcelService()
            excel_bytes = exporter.export(
                assessment,
                {
                    key: value
                    for key, value in decisions.items()
                    if isinstance(value, ReviewerDecisionRecord)
                },
                document_number,
                revision,
                reviewer or "Reviewer",
            )

            # Add approved manual comments to the same workbook.
            workbook = load_workbook(BytesIO(excel_bytes))
            worksheet = workbook["CRS"]

            for manual in manual_comments:
                row = [
                    f"CR-{worksheet.max_row:03d}",
                    document_number,
                    revision,
                    f"PDF p. {manual['page']} — {manual['section']}",
                    manual["comment"],
                    manual["category"],
                    manual["criticality"],
                    reviewer or "Reviewer",
                    __import__("datetime").date.today().isoformat(),
                    None,
                    None,
                    "Open",
                    None,
                ]
                worksheet.append(row)

            output = BytesIO()
            workbook.save(output)
            output.seek(0)

            st.download_button(
                "Download PMEC CRS Excel",
                data=output.getvalue(),
                file_name="GeoDocumentReviewer_CRS.xlsx",
                mime=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            )

            if not approved_ai and not manual_comments:
                st.info(
                    "The workbook contains the CRS headers but no approved "
                    "comments. No AI suggestions were automatically approved."
                )

        except Exception as exc:
            st.error(f"Excel generation failed: {exc}")
else:
    st.info(
        "Upload a PDF and run the review to begin. "
        "Your PDF is processed locally before its extracted text is sent "
        "to OpenRouter."
    )
