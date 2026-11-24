from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReviewDecision(StrEnum):
    COMMENT_REQUIRED = "COMMENT_REQUIRED"
    NO_COMMENT_REQUIRED = "NO_COMMENT_REQUIRED"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


class ReviewCategory(StrEnum):
    TECHNICAL = "Technical"
    EDITORIAL = "Editorial"
    CLARIFICATION = "Clarification"


class Criticality(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Confidence(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ReviewerStatus(StrEnum):
    PENDING = "Pending"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"


class ReviewEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    pdf_page: int = Field(ge=1)
    section: str | None = None
    observation: str = Field(min_length=1)


class ReviewFinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    finding_id: str = Field(default_factory=lambda: str(uuid4()))
    topic: str = Field(min_length=1)
    decision: ReviewDecision
    proposed_comment: str | None = None
    category: ReviewCategory | None = None
    criticality: Criticality | None = None
    supporting_evidence: tuple[ReviewEvidence, ...] = ()
    reasoning: str = Field(min_length=1)
    information_gaps: tuple[str, ...] = ()
    confidence: Confidence

    @model_validator(mode="after")
    def validate_finding(self):
        if self.decision == ReviewDecision.COMMENT_REQUIRED:
            if not self.proposed_comment or not self.proposed_comment.strip():
                raise ValueError("A proposed comment is required.")
            if not self.supporting_evidence:
                raise ValueError("Supporting evidence is required.")
            if self.category is None or self.criticality is None:
                raise ValueError("Category and criticality are required.")
        elif self.proposed_comment is not None:
            raise ValueError("A comment is only allowed for COMMENT_REQUIRED.")
        return self


class ReviewAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_file: str = Field(min_length=1)
    page_count: int = Field(gt=0)
    model_name: str = Field(min_length=1)
    findings: tuple[ReviewFinding, ...]

    @model_validator(mode="after")
    def validate_findings(self):
        ids = [finding.finding_id for finding in self.findings]
        if len(ids) != len(set(ids)):
            raise ValueError("Finding IDs must be unique.")

        for finding in self.findings:
            for evidence in finding.supporting_evidence:
                if evidence.pdf_page > self.page_count:
                    raise ValueError(
                        f"Evidence page {evidence.pdf_page} exceeds the document page count."
                    )
        return self


class ReviewerDecisionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    finding_id: str = Field(min_length=1)
    status: ReviewerStatus = ReviewerStatus.PENDING
    final_comment: str | None = None
    reviewer_notes: str | None = None

    @model_validator(mode="after")
    def validate_decision(self):
        if self.status == ReviewerStatus.ACCEPTED:
            if not self.final_comment or not self.final_comment.strip():
                raise ValueError("Accepted findings need a final comment.")
        if self.status == ReviewerStatus.REJECTED and self.final_comment is not None:
            raise ValueError("Rejected findings cannot have a final comment.")
        return self
