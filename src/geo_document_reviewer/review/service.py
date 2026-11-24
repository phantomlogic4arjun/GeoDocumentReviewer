import json
import re

import httpx

from geo_document_reviewer.config.settings import settings
from geo_document_reviewer.orchestration.models import ProcessedDocument
from geo_document_reviewer.review.models import (
    Confidence,
    Criticality,
    ReviewAssessment,
    ReviewCategory,
    ReviewDecision,
    ReviewEvidence,
    ReviewFinding,
)
from geo_document_reviewer.review.prompts.engineering_review import SYSTEM_PROMPT


class ReviewServiceError(Exception):
    """Raised when an AI review cannot be completed."""


class ReviewService:
    """Runs an evidence-based geotechnical review using OpenRouter."""

    def review(
        self,
        document: ProcessedDocument,
        topics: list[str],
    ) -> tuple[ReviewAssessment, dict]:
        api_key = settings.openrouter_api_key
        if not api_key:
            raise ReviewServiceError("OPENROUTER_API_KEY is missing from the project .env file.")

        report_text = "\n\n".join(
            f"--- PDF PAGE {page.page_number} ---\n{page.review_text}" for page in document.pages
        )

        user_prompt = (
            f"Review file: {document.file_name}\n"
            f"Total PDF pages: {document.page_count}\n"
            f"Topics to assess: {', '.join(topics)}\n\n"
            f"BEGIN REPORT\n{report_text}\nEND REPORT"
        )

        payload = {
            "model": settings.openrouter_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 3500,
            "reasoning": {"enabled": False},
        }

        try:
            response = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=600,
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]

            if not content:
                raise ReviewServiceError("The AI returned an empty response.")

            content = re.sub(
                r"^\s*```(?:json)?\s*|\s*```\s*$",
                "",
                content.strip(),
            )
            parsed = json.loads(content)

            findings = []
            for item in parsed["assessments"]:
                decision = ReviewDecision(item["decision"])
                comment = item.get("proposed_comment")

                findings.append(
                    ReviewFinding(
                        topic=item["topic"],
                        decision=decision,
                        proposed_comment=comment,
                        category=(
                            ReviewCategory(item["category"]) if item.get("category") else None
                        ),
                        criticality=(
                            Criticality(item["criticality"]) if item.get("criticality") else None
                        ),
                        supporting_evidence=tuple(
                            ReviewEvidence(**evidence)
                            for evidence in item.get("supporting_evidence", [])
                        ),
                        reasoning=item["reasoning"],
                        information_gaps=tuple(item.get("information_gaps", [])),
                        confidence=Confidence(item["confidence"]),
                    )
                )

            assessment = ReviewAssessment(
                source_file=document.file_name,
                page_count=document.page_count,
                model_name=result.get("model", settings.openrouter_model),
                findings=tuple(findings),
            )

            return assessment, result.get("usage", {})

        except ReviewServiceError:
            raise
        except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
            raise ReviewServiceError(f"Unable to complete or validate AI review: {exc}") from exc
