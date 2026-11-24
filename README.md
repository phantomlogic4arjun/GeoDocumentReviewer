# GeoDocumentReviewer

A local-first, cross-platform application for reviewing Geotechnical Interpretative Reports (GIRs) and generating proposed comments in the PMEC Comment Resolution Sheet (CRS) format.

## Project Goals

GeoDocumentReviewer is intended to:

- Extract information from Geotechnical Interpretative Reports.
- Identify potential technical errors, inconsistencies, and missing information.
- Review reports against project-specific requirements and general geotechnical review criteria.
- Generate evidence-supported, actionable review comments.
- Allow a human reviewer to approve, edit, or reject proposed comments.
- Populate the approved comments into the existing PMEC CRS Excel template.

The application supports engineering review. It does not replace professional engineering judgment or certify engineering designs or calculations.

## Architecture

- Python 3.12
- Streamlit user interface
- Ollama local LLM runtime
- PyMuPDF PDF extraction
- openpyxl Excel processing
- Pydantic data validation
- HTTPX for model-provider communication
- pytest automated testing
- Ruff code quality

The application is designed to run on individual macOS and Windows workstations.

## Prerequisites

- Python 3.12
- Git
- Ollama
- A compatible local language model

## macOS Setup

Clone the repository:

    git clone <repository-url>
    cd GeoDocumentReviewer

Create a virtual environment:

    python3.12 -m venv .venv

Activate it:

    source .venv/bin/activate

Install the project:

    python -m pip install --upgrade pip
    python -m pip install -e ".[dev]"

## Windows Setup

Clone the repository:

    git clone <repository-url>
    cd GeoDocumentReviewer

Create a virtual environment:

    py -3.12 -m venv .venv

Activate it in PowerShell:

    .venv\Scripts\Activate.ps1

Install the project:

    python -m pip install --upgrade pip
    python -m pip install -e ".[dev]"

## Configuration

Copy `.env.example` to `.env`.

macOS:

    cp .env.example .env

Windows PowerShell:

    Copy-Item .env.example .env

Configure the local model settings in `.env` as needed.

Default configuration:

    LLM_PROVIDER=ollama
    OLLAMA_BASE_URL=http://localhost:11434
    LLM_MODEL=qwen3:8b

## Local Model Runtime

Install Ollama separately on the workstation.

Ensure the Ollama service is running and the configured model is available before using AI review functionality.

Model selection is configurable and is not tied to a specific model family.

## Running Tests

Run all automated tests:

    pytest -v

Check code quality:

    ruff check .

Check formatting:

    ruff format --check .

Check dependencies:

    python -m pip check

## Project Structure

    GeoDocumentReviewer/
    ├── src/
    │   └── geo_document_reviewer/
    │       ├── ingestion/
    │       ├── extraction/
    │       ├── review/
    │       │   ├── criteria/
    │       │   ├── prompts/
    │       │   └── models/
    │       ├── orchestration/
    │       ├── validation/
    │       ├── comments/
    │       ├── excel/
    │       └── config/
    ├── tests/
    │   ├── unit/
    │   ├── integration/
    │   └── cross_platform/
    ├── templates/
    ├── input/
    │   ├── reports/
    │   ├── specifications/
    │   └── previous_revisions/
    └── output/

## Data Confidentiality

- Project reports and specifications are not intended to be committed to Git.
- Generated review documents remain in the local output directory.
- Local model inference is the default design.
- External APIs must not be used unless the relevant document owner authorizes their use.
- Verify that all processing components remain local before handling confidential documents.

## Development Guidelines

- Keep application code platform-independent.
- Use `pathlib` for filesystem operations.
- Avoid hardcoded workstation-specific paths.
- Keep model integrations behind a provider abstraction.
- Add automated tests for new functionality.
- Preserve the original CRS template layout and formatting.
- Require human approval before exporting proposed comments.

## Project Status

Early development: initial project structure, configuration, and automated tests established.
