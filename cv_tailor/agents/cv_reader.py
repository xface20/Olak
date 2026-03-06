"""Agent for extracting structured content from CV PDFs."""

import pdfplumber
from anthropic import Anthropic

EXTRACTION_PROMPT = """You are an expert CV/resume parser. Extract ALL content from this CV text into a structured format.

Return a JSON object with these sections (include only sections that exist in the CV):
{
  "personal_info": {
    "name": "",
    "title": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin": "",
    "website": ""
  },
  "professional_summary": "",
  "experience": [
    {
      "company": "",
      "title": "",
      "dates": "",
      "location": "",
      "achievements": [""]
    }
  ],
  "education": [
    {
      "institution": "",
      "degree": "",
      "dates": "",
      "details": ""
    }
  ],
  "skills": {
    "technical": [""],
    "leadership": [""],
    "tools": [""],
    "certifications": [""],
    "languages": [""]
  },
  "additional_sections": {}
}

Preserve ALL details, metrics, numbers, and achievements exactly as written. Do not summarize or omit anything.

CV Text:
"""


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract raw text from a PDF file using pdfplumber."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def parse_cv(pdf_path: str, client: Anthropic) -> dict:
    """Extract and structure CV content from a PDF file.

    Uses pdfplumber for text extraction and Claude Haiku for fast structuring.
    """
    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text.strip():
        raise ValueError(f"No text could be extracted from {pdf_path}")

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": EXTRACTION_PROMPT + raw_text,
            }
        ],
    )

    import json
    content = response.content[0].text
    # Extract JSON from response (handle markdown code blocks)
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    return {"raw_text": raw_text, "structured": json.loads(content.strip())}
