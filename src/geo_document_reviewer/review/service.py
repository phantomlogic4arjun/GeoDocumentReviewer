import json
import re
import threading

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


class ReviewCancelledError(ReviewServiceError):
    """Raised when an AI review is cancelled by the user."""


class ReviewCancellation:
    """Coordinates cancellation between the UI and the review worker."""

    def __init__(self):
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._response = None

    @property
    def cancelled(self):
        return self._event.is_set()

    def attach_response(self, response):
        with self._lock:
            self._response = response
            should_close = self.cancelled

        if should_close:
            response.close()

    def detach_response(self, response):
        """Release the response reference when streaming finishes."""
        with self._lock:
            if self._response is response:
                self._response = None

    def cancel(self):
        self._event.set()

        with self._lock:
            response = self._response

        if response is not None:
            response.close()

    def raise_if_cancelled(self):
        if self.cancelled:
            raise ReviewCancelledError("Review cancelled by user.")


class ReviewService:
    """Runs evidence-based geotechnical reviews using Ollama or OpenRouter."""

    def __init__(self, provider: str = "openrouter", model: str | None = None):
        self.provider = provider.lower()
        self.model = model

        if self.provider not in {"ollama", "openrouter"}:
            raise ReviewServiceError(f"Unsupported AI provider: {provider}")

    @staticmethod
    def list_ollama_models() -> list[str]:
        """Discover models installed in the local Ollama instance."""
        try:
            response = httpx.get(
                f"{settings.ollama_base_url.rstrip('/')}/api/tags",
                timeout=10,
            )
            response.raise_for_status()

            return sorted(
                model["name"] for model in response.json().get("models", []) if model.get("name")
            )

        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise ReviewServiceError(
                "Cannot connect to Ollama. Make sure Ollama is running."
            ) from exc

    @staticmethod
    def list_openrouter_models() -> list[str]:
        """Retrieve available model identifiers from OpenRouter."""
        try:
            response = httpx.get(
                "https://openrouter.ai/api/v1/models",
                timeout=20,
            )
            response.raise_for_status()

            return sorted(
                model["id"] for model in response.json().get("data", []) if model.get("id")
            )

        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise ReviewServiceError("Unable to retrieve OpenRouter models.") from exc

    def review(
        self,
        document: ProcessedDocument,
        topics: list[str],
        cancellation: ReviewCancellation | None = None,
    ) -> tuple[ReviewAssessment, dict]:
        """Review a processed document using the selected provider."""

        if not topics:
            raise ReviewServiceError("Select at least one review topic.")

        if not self.model:
            raise ReviewServiceError("An AI model must be selected.")

        if cancellation:
            cancellation.raise_if_cancelled()

        model = self.model

        report_text = "\n\n".join(
            f"--- PDF PAGE {page.page_number} ---\n{page.review_text}" for page in document.pages
        )

        user_prompt = (
            f"Review file: {document.file_name}\n"
            f"Total PDF pages: {document.page_count}\n"
            f"Topics to assess: {', '.join(topics)}\n\n"
            f"BEGIN REPORT\n{report_text}\nEND REPORT"
        )

        try:
            if self.provider == "ollama":
                content, usage, actual_model = self._review_ollama(
                    model,
                    user_prompt,
                    cancellation,
                )
            else:
                content, usage, actual_model = self._review_openrouter(
                    model,
                    user_prompt,
                )

            if cancellation:
                cancellation.raise_if_cancelled()

            parsed = self._parse_content(content)

            findings = tuple(
                ReviewFinding(
                    topic=item["topic"],
                    decision=ReviewDecision(item["decision"]),
                    proposed_comment=item.get("proposed_comment"),
                    category=(ReviewCategory(item["category"]) if item.get("category") else None),
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
                for item in parsed["assessments"]
            )

            assessment = ReviewAssessment(
                source_file=document.file_name,
                page_count=document.page_count,
                model_name=f"{self.provider}: {actual_model}",
                findings=findings,
            )

            return assessment, usage

        except ReviewServiceError:
            raise

        except (
            httpx.HTTPError,
            KeyError,
            ValueError,
            TypeError,
            IndexError,
        ) as exc:
            raise ReviewServiceError(f"Unable to complete or validate AI review: {exc}") from exc

    def _review_ollama(
        self,
        model: str,
        user_prompt: str,
        cancellation: ReviewCancellation | None = None,
    ) -> tuple[str, dict, str]:
        """Stream the local Ollama response and support cancellation."""

        content_parts = []
        final_result = {}

        try:
            with httpx.stream(
                "POST",
                f"{settings.ollama_base_url.rstrip('/')}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "format": "json",
                    "stream": True,
                    "options": {
                        "temperature": 0.1,
                    },
                },
                timeout=httpx.Timeout(900, connect=10),
            ) as response:
                if cancellation:
                    cancellation.attach_response(response)

                try:
                    if cancellation:
                        cancellation.raise_if_cancelled()

                    response.raise_for_status()

                    for line in response.iter_lines():
                        if cancellation:
                            cancellation.raise_if_cancelled()

                        if not line:
                            continue

                        chunk = json.loads(line)

                        message = chunk.get("message", {})
                        text = message.get("content", "")

                        if text:
                            content_parts.append(text)

                        if chunk.get("done"):
                            final_result = chunk

                finally:
                    if cancellation:
                        cancellation.detach_response(response)

            if cancellation:
                cancellation.raise_if_cancelled()

        except httpx.HTTPError as exc:
            if cancellation and cancellation.cancelled:
                raise ReviewCancelledError("Review cancelled by user.") from exc

            raise ReviewServiceError(f"Unable to communicate with Ollama: {exc}") from exc

        content = "".join(content_parts)

        if not content:
            raise ReviewServiceError("Ollama returned an empty response.")

        usage = {
            "prompt_tokens": final_result.get("prompt_eval_count", 0),
            "completion_tokens": final_result.get("eval_count", 0),
            "cost": None,
        }

        return content, usage, final_result.get("model", model)

    def _review_openrouter(
        self,
        model: str,
        user_prompt: str,
    ) -> tuple[str, dict, str]:
        """Send the review request to OpenRouter."""

        api_key = settings.openrouter_api_key

        if not api_key:
            raise ReviewServiceError("OPENROUTER_API_KEY is missing from the project .env file.")

        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 3500,
                "reasoning": {"enabled": False},
            },
            timeout=900,
        )
        response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))

        if not content:
            raise ReviewServiceError("OpenRouter returned an empty response.")

        return (
            content,
            result.get("usage", {}),
            result.get("model", model),
        )

    @staticmethod
    def _parse_content(content: str) -> dict:
        """Parse the model response and validate its top-level structure."""

        content = re.sub(
            r"^\s*```(?:json)?\s*|\s*```\s*$",
            "",
            content.strip(),
        )

        try:
            parsed = json.loads(content)

        except json.JSONDecodeError as exc:
            raise ReviewServiceError(f"The model did not return valid JSON: {exc}") from exc

        if not isinstance(parsed, dict) or not isinstance(parsed.get("assessments"), list):
            raise ReviewServiceError("The model response must contain an assessments list.")

        return parsed
