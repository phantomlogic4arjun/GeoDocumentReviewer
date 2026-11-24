from geo_document_reviewer.review.models import (
    ReviewAssessment,
    ReviewDecision,
    ReviewerDecisionRecord,
    ReviewerStatus,
)


def accepted_comments(
    assessment: ReviewAssessment,
    decisions: dict[str, ReviewerDecisionRecord],
) -> list[tuple]:
    """Return only human-approved comments suitable for CRS export."""
    result = []

    for finding in assessment.findings:
        decision = decisions.get(finding.finding_id)

        if (
            decision is None
            or decision.status != ReviewerStatus.ACCEPTED
            or finding.decision != ReviewDecision.COMMENT_REQUIRED
        ):
            continue

        result.append((finding, decision))

    return result
