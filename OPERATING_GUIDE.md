# GeoDocumentReviewer — Operating Guide

## 1. Purpose

GeoDocumentReviewer assists engineers with reviewing Geotechnical Interpretative Reports (GIRs) and preparing comments for a Comment Resolution Sheet (CRS).

The application provides:

- PDF ingestion and text extraction.
- OCR for scanned or image-based PDF pages.
- AI-assisted technical review.
- Evidence and PDF page references for proposed findings.
- Local Ollama and cloud OpenRouter review options.
- Comparison of assessments from different AI providers.
- Human review and approval of proposed comments.
- CRS Excel generation.

**Important:** GeoDocumentReviewer is an engineering review assistant. It does not replace qualified engineering judgment and does not automatically approve or issue comments.

## 2. System Requirements

The Windows environment requires:

- Windows 10 or Windows 11.
- Git for Windows.
- Python 3.12.
- Tesseract OCR.
- Internet access when using OpenRouter.
- Ollama installed locally when using local AI review.

The application uses Python, Streamlit, PyMuPDF, Pydantic, openpyxl, and other dependencies declared in `pyproject.toml`.

## 3. Obtain the Application

Install Git for Windows if it is not already installed.

Open PowerShell and clone the repository:

```powershell
git clone https://github.com/phantomlogic4arjun/GeoDocumentReviewer.git
cd GeoDocumentReviewer
```

If PowerShell blocks script execution, allow scripts for the current PowerShell session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Run the setup script:

```powershell
.\setup_windows.ps1
```

The setup script:

1. Checks for Git and Windows Package Manager.
2. Checks for Python 3.12 and attempts installation if it is missing.
3. Creates a Python virtual environment.
4. Installs application and development dependencies.
5. Checks for Tesseract OCR and attempts installation if necessary.
6. Creates `.env` from `.env.example` if `.env` does not already exist.
7. Configures the standard Tesseract executable path when available.

If Python is installed during setup, restart PowerShell, return to the project directory, and run the setup script again.

The setup script does not overwrite an existing `.env` file.

## 4. Configure AI Providers

Open `.env` in a text editor.

### 4.1 OpenRouter — Cloud AI

To use OpenRouter, configure your API key:

```dotenv
OPENROUTER_API_KEY=your_api_key_here
```

Replace the placeholder with your actual API key.

Keep the key private. Never commit `.env` to Git or share it with others.

The application retrieves available OpenRouter models when model discovery is available. The model selection is made within the application.

**Data protection:** When OpenRouter is selected, extracted report content is sent to the selected cloud model for review.

Before sending project documents to an external provider, obtain the necessary organizational approval and verify applicable confidentiality, contractual, and data-handling requirements.

### 4.2 Ollama — Local AI

Install Ollama from:

https://ollama.com/

Start Ollama and download a model supported by your computer.

For example:

```powershell
ollama pull qwen3:8b
```

Check installed models:

```powershell
ollama list
```

The application discovers models from the local Ollama service.

Local inference sends review requests to the configured Ollama service rather than OpenRouter. Confirm that Ollama is running before selecting local review.

The actual performance of a local model depends on the model size, quantization, available memory, and complexity of the report.

## 5. Start the Application

From the project directory, run:

```powershell
.\run_windows.ps1
```

Streamlit starts the application and displays a local address, usually:

```text
http://localhost:8501
```

Open this address in your browser.

To stop the application, press `Ctrl+C` in the PowerShell window.

## 6. Review Workflow

### Step 1 — Prepare the Documents

Provide the required GIR PDF and CRS Excel template through the application.

Before starting, verify:

- The correct project report is selected.
- The report is the intended revision.
- The correct CRS template is selected.
- The documents belong to the same project and review package.

Keep original project documents unchanged.

### Step 2 — Select a Review Mode

The application supports three review modes.

**OpenRouter only**

Uses a selected cloud model for the review.

**Local Ollama only**

Uses a locally installed Ollama model.

**Compare both**

Runs the local and cloud providers against the same processed document and presents their assessments for comparison.

When OpenRouter is involved, the application requires explicit consent before making the cloud request.

This application-level consent does not replace organizational approval for external data sharing.

### Step 3 — Examine the Assessments

Review the findings produced by the selected model or models.

Pay attention to:

- Review decision.
- Supporting evidence.
- Referenced PDF pages.
- Proposed comment wording.
- Category.
- Criticality.
- Confidence.

The model may identify a potential issue, request clarification, or determine that no comment is required.

Do not assume that a finding is correct simply because it is confidently worded.

Verify the finding against the original report, project requirements, specifications, drawings, and applicable engineering standards.

### Step 4 — Compare AI Providers

When using Compare both, examine:

- Whether both providers identify the same issue.
- Whether their decisions agree.
- Whether they reference the same evidence pages.
- Whether their proposed comments differ.
- Whether one provider identifies an issue missed by the other.

Agreement between two models is not proof of technical correctness.

Disagreement should be treated as a reason for closer engineering review, not as an automatic indication that one model is correct.

### Step 5 — Make Reviewer Decisions

Each proposed AI comment requires a human decision.

The reviewer can:

- Accept a proposed comment.
- Reject a proposed comment.
- Leave a proposed comment pending.

Where appropriate, edit the final comment wording before acceptance.

Reviewers can also enter manual comments for issues identified independently of the AI assessment.

No AI finding is automatically approved.

### Step 6 — Export the CRS

Export the CRS workbook after completing the reviewer decisions.

The export workflow includes accepted AI findings and manually entered comments.

Before issuing the workbook, verify:

- Comment wording.
- Document number.
- Revision.
- Section and page references.
- Category and criticality.
- Raised-by information.
- Workbook structure and formatting.
- Completeness of the exported comments.

A CRS containing only its headers when no comments have been accepted can be a valid result. Do not add comments merely to populate the spreadsheet.

The reviewer remains responsible for the final issued CRS.

## 7. Data Handling and Security

Follow these precautions:

- Do not commit `.env`, API keys, confidential reports, or generated project deliverables to Git.
- Obtain organizational approval before sending project content to cloud AI providers.
- Keep original project documents unchanged.
- Verify all AI-generated evidence references against the source PDF