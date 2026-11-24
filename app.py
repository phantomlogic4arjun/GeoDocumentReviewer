from datetime import date
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import streamlit as st
from openpyxl import load_workbook

from geo_document_reviewer.comments.service import accepted_comments
from geo_document_reviewer.excel.service import CrsExcelService
from geo_document_reviewer.orchestration.service import DocumentProcessingService
from geo_document_reviewer.review.models import (
    ReviewDecision,
    ReviewerDecisionRecord,
    ReviewerStatus,
)
from geo_document_reviewer.review.service import (
    ReviewService,
    ReviewServiceError,
)

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


@st.cache_data(ttl=300, show_spinner=False)
def get_ollama_models():
    return ReviewService.list_ollama_models()


@st.cache_data(ttl=300, show_spinner=False)
def get_openrouter_models():
    return ReviewService.list_openrouter_models()


with st.sidebar:
    st.header("Review configuration")

    document_number = st.text_input(
        "Document number",
        value="",
    )
    revision = st.text_input("Revision", value="0")
    reviewer = st.text_input("Reviewer name")

    topics = st.multiselect(
        "Review topics",
        ["Settlement", "Groundwater"],
        default=["Settlement", "Groundwater"],
    )

    st.divider()
    st.subheader("AI provider")

    review_mode = st.selectbox(
        "Review mode",
        [
            "OpenRouter only",
            "Local Ollama only",
            "Compare both",
        ],
    )

    ollama_model = None
    openrouter_model = None
    cloud_consent = False

    if review_mode in ["Local Ollama only", "Compare both"]:
        try:
            local_models = get_ollama_models()
        except ReviewServiceError as exc:
            local_models = []
            st.warning(str(exc))

        if local_models:
            configured_local = "qwen3:8b"

            default_local = (
                configured_local if configured_local in local_models else local_models[0]
            )

            ollama_model = st.selectbox(
                "Local Ollama model",
                local_models,
                index=local_models.index(default_local),
            )
        else:
            st.error("No Ollama models found. Start Ollama and install a model.")

    if review_mode in ["OpenRouter only", "Compare both"]:
        try:
            cloud_models = get_openrouter_models()
        except ReviewServiceError as exc:
            cloud_models = []
            st.warning(str(exc))

        configured_cloud = "qwen/qwen3.8-flash"

        if cloud_models:
            default_cloud = (
                configured_cloud if configured_cloud in cloud_models else cloud_models[0]
            )

            openrouter_model = st.selectbox(
                "OpenRouter model",
                cloud_models,
                index=cloud_models.index(default_cloud),
            )
        else:
            openrouter_model = st.text_input(
                "OpenRouter model ID",
                value=configured_cloud,
                help="Enter a model identifier supported by OpenRouter.",
            )

        cloud_consent = st.checkbox(
            "I authorize sending extracted report text to OpenRouter.",
            value=False,
            help=(
                "The PDF is processed locally, but its extracted text is "
                "sent to the selected OpenRouter model."
            ),
        )

        st.caption(
            "Check your organization's confidentiality and data-sharing "
            "requirements before using cloud processing."
        )

uploaded_file = st.file_uploader(
    "Upload a geotechnical PDF",
    type=["pdf"],
)

if uploaded_file is not None:
    st.write(f"**Selected report:** {uploaded_file.name}")
    st.write(f"**File size:** {uploaded_file.size / (1024 * 1024):.2f} MB")

    if st.button("Process PDF and run AI review", type="primary"):
        if not topics:
            st.error("Select at least one review topic.")

        elif review_mode in ["Local Ollama only", "Compare both"] and not ollama_model:
            st.error("A local Ollama model is required for this mode.")

        elif review_mode in ["OpenRouter only", "Compare both"] and not openrouter_model:
            st.error("An OpenRouter model is required for this mode.")

        elif review_mode in ["OpenRouter only", "Compare both"] and not cloud_consent:
            st.error(
                "Authorize sending extracted report text to OpenRouter before running this mode."
            )

        else:
            try:
                with st.spinner("Processing PDF locally..."):
                    with TemporaryDirectory() as temp_dir:
                        pdf_path = Path(temp_dir) / uploaded_file.name
                        pdf_path.write_bytes(uploaded_file.getvalue())

                        processed = DocumentProcessingService().process(pdf_path)

                        st.session_state["processed_page_count"] = processed.page_count
                        st.session_state["processed_file"] = uploaded_file.name

                        results = {}

                        if review_mode in [
                            "Local Ollama only",
                            "Compare both",
                        ]:
                            with st.spinner(f"Reviewing with local model {ollama_model}..."):
                                results["Local Ollama"] = ReviewService(
                                    provider="ollama",
                                    model=ollama_model,
                                ).review(processed, topics)

                        if review_mode in [
                            "OpenRouter only",
                            "Compare both",
                        ]:
                            with st.spinner(
                                f"Reviewing with OpenRouter model {openrouter_model}..."
                            ):
                                results["OpenRouter"] = ReviewService(
                                    provider="openrouter",
                                    model=openrouter_model,
                                ).review(processed, topics)

                st.session_state["review_results"] = results

                initial_provider = (
                    "Local Ollama" if review_mode == "Local Ollama only" else "OpenRouter"
                )

                st.session_state["active_result"] = initial_provider
                st.session_state["decisions"] = {}
                st.session_state["manual_comments"] = []

                st.success("Review completed.")

            except (ValueError, RuntimeError, ReviewServiceError) as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Processing failed: {exc}")

results = st.session_state.get("review_results", {})

if results:
    st.divider()
    st.subheader("Model comparison")

    if len(results) == 2:
        local_assessment, local_usage = results["Local Ollama"]
        cloud_assessment, cloud_usage = results["OpenRouter"]

        left, right = st.columns(2)

        for column, provider_name, assessment, usage in [
            (
                left,
                "Local Ollama",
                local_assessment,
                local_usage,
            ),
            (
                right,
                "OpenRouter",
                cloud_assessment,
                cloud_usage,
            ),
        ]:
            with column:
                st.markdown(f"**{provider_name}**")
                st.write(f"Model: `{assessment.model_name}`")
                st.metric("Findings", len(assessment.findings))

                comment_count = sum(
                    finding.decision == ReviewDecision.COMMENT_REQUIRED
                    for finding in assessment.findings
                )

                human_review_count = sum(
                    finding.decision == ReviewDecision.NEEDS_HUMAN_REVIEW
                    for finding in assessment.findings
                )

                st.write(f"Comments required: {comment_count}")
                st.write(f"Needs human review: {human_review_count}")

                cost = usage.get("cost")
                st.write(
                    f"Reported cost: ${cost:.6f}"
                    if cost is not None
                    else "Reported cost: Not available"
                )

        local_by_topic = {finding.topic: finding for finding in local_assessment.findings}

        cloud_by_topic = {finding.topic: finding for finding in cloud_assessment.findings}

        comparison_rows = []

        all_topics = sorted(set(local_by_topic) | set(cloud_by_topic))

        for topic in all_topics:
            local_finding = local_by_topic.get(topic)
            cloud_finding = cloud_by_topic.get(topic)

            local_decision = local_finding.decision.value if local_finding else "Missing"

            cloud_decision = cloud_finding.decision.value if cloud_finding else "Missing"

            local_pages = (
                ", ".join(str(evidence.pdf_page) for evidence in local_finding.supporting_evidence)
                if local_finding
                else ""
            )

            cloud_pages = (
                ", ".join(str(evidence.pdf_page) for evidence in cloud_finding.supporting_evidence)
                if cloud_finding
                else ""
            )

            local_comment = local_finding.proposed_comment or "" if local_finding else ""

            cloud_comment = cloud_finding.proposed_comment or "" if cloud_finding else ""

            comparison_rows.append(
                {
                    "Topic": topic,
                    "Local conclusion": local_decision,
                    "OpenRouter conclusion": cloud_decision,
                    "Same conclusion": (
                        "Yes"
                        if local_finding
                        and cloud_finding
                        and local_finding.decision == cloud_finding.decision
                        else "No"
                    ),
                    "Local evidence pages": local_pages,
                    "OpenRouter evidence pages": cloud_pages,
                    "Local proposed comment": local_comment,
                    "OpenRouter proposed comment": cloud_comment,
                }
            )

        st.dataframe(
            comparison_rows,
            use_container_width=True,
            hide_index=True,
        )

        st.info(
            "The comparison shows differences between model outputs. "
            "It does not establish which engineering conclusion is correct."
        )

    st.divider()
    st.subheader("Select assessment for engineering review")

    provider_names = list(results.keys())
    previous_provider = st.session_state.get(
        "active_result",
        provider_names[0],
    )

    if previous_provider not in provider_names:
        previous_provider = provider_names[0]

    active_provider = st.selectbox(
        "Assessment to use for reviewer decisions and CRS export",
        provider_names,
        index=provider_names.index(previous_provider),
    )

    if active_provider != previous_provider:
        st.session_state["active_result"] = active_provider
        st.session_state["decisions"] = {}
        st.session_state["manual_comments"] = []

        # Clear Streamlit widget values from the previous assessment.
        for key in list(st.session_state.keys()):
            if key.startswith(("comment_", "status_", "notes_")):
                del st.session_state[key]

        st.warning(
            "The selected assessment changed. Previous reviewer decisions "
            "and manual comments were cleared to prevent applying them "
            "to a different model's findings."
        )

    assessment, usage = results[active_provider]

    st.subheader("Document processing")

    col1, col2, col3 = st.columns(3)

    col1.metric("PDF pages", assessment.page_count)
    col2.metric("Review findings", len(assessment.findings))

    cost = usage.get("cost")

    col3.metric(
        "Model cost",
        f"${cost:.6f}" if cost is not None else "Not reported",
    )

    st.caption(
        f"Provider: {active_provider} | "
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

                existing = decisions.get(finding.finding_id)

                default_comment = (
                    existing.final_comment
                    if existing and existing.final_comment
                    else finding.proposed_comment or ""
                )

                edited_comment = st.text_area(
                    "Edit the proposed comment",
                    value=default_comment,
                    key=f"comment_{finding.finding_id}",
                )

                current_status = existing.status.value if existing else ReviewerStatus.PENDING.value

                selected_status = st.selectbox(
                    "Reviewer decision",
                    [item.value for item in ReviewerStatus],
                    index=[item.value for item in ReviewerStatus].index(current_status),
                    key=f"status_{finding.finding_id}",
                )

                notes = st.text_input(
                    "Reviewer notes",
                    value=(existing.reviewer_notes or "" if existing else ""),
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

        add_manual = st.form_submit_button("Add manual comment")

    if add_manual:
        if manual_comment.strip():
            st.session_state.setdefault(
                "manual_comments",
                [],
            ).append(
                {
                    "topic": manual_topic,
                    "page": int(manual_page),
                    "section": manual_section,
                    "comment": manual_comment.strip(),
                    "category": manual_category,
                    "criticality": manual_criticality,
                }
            )

            st.success("Manual comment added.")
        else:
            st.error("Enter a comment first.")

    manual_comments = st.session_state.get(
        "manual_comments",
        [],
    )

    approved_ai = accepted_comments(
        assessment,
        {
            key: value
            for key, value in decisions.items()
            if isinstance(value, ReviewerDecisionRecord)
        },
    )

    st.divider()
    st.subheader("CRS export")

    st.metric(
        "Approved comments",
        len(approved_ai) + len(manual_comments),
    )

    if st.button("Generate CRS Excel"):
        try:
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

            workbook = load_workbook(BytesIO(excel_bytes))
            worksheet = workbook["CRS"]

            for manual in manual_comments:
                worksheet.append(
                    [
                        f"CR-{worksheet.max_row:03d}",
                        document_number,
                        revision,
                        (f"PDF p. {manual['page']} — {manual['section']}"),
                        manual["comment"],
                        manual["category"],
                        manual["criticality"],
                        reviewer or "Reviewer",
                        date.today().isoformat(),
                        None,
                        None,
                        "Open",
                        None,
                    ]
                )

            output = BytesIO()
            workbook.save(output)
            output.seek(0)

            st.download_button(
                "Download CRS Excel",
                data=output.getvalue(),
                file_name="GeoDocumentReviewer_CRS.xlsx",
                mime=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            )

            if not approved_ai and not manual_comments:
                st.info(
                    "The workbook contains CRS headers but no approved "
                    "comments. No AI suggestions were automatically approved."
                )

        except Exception as exc:
            st.error(f"Excel generation failed: {exc}")

else:
    st.info(
        "Upload a PDF and run a review to begin. "
        "Choose Local Ollama, OpenRouter, or Compare Both in the sidebar."
    )
