"""Agent for generating a tailored cover letter."""

import json
from anthropic import Anthropic

COVER_LETTER_PROMPT = """You are an elite executive cover letter writer. Craft a compelling, personalized cover letter.

RULES:
- Address specific role requirements with concrete examples from the candidate's experience
- Open with a strong hook that shows genuine interest and relevant achievement
- Middle paragraphs should map 2-3 key role requirements to the candidate's strongest matching experiences
- Close with confidence and a clear call to action
- Tone: Professional, confident, authentic — not generic or sycophantic
- Length: 3-4 paragraphs, approximately 300-400 words
- NEVER fabricate experiences or qualifications not in the CV
- Reference the specific company and role by name
- Include quantified achievements where possible

Return a JSON object:
{{
  "salutation": "Dear Hiring Manager,",
  "paragraphs": [
    "Opening paragraph...",
    "Body paragraph 1...",
    "Body paragraph 2...",
    "Closing paragraph..."
  ],
  "sign_off": "Sincerely,",
  "candidate_name": ""
}}

CV Data:
{cv_data}

Role Requirements:
{role_data}

Gap Analysis:
{gap_analysis}
"""


def generate_cover_letter(
    cv_data: dict, role_data: dict, gap_analysis: dict, client: Anthropic
) -> dict:
    """Generate a tailored cover letter using Opus for highest quality."""
    prompt = COVER_LETTER_PROMPT.format(
        cv_data=json.dumps(cv_data, indent=2),
        role_data=json.dumps(role_data, indent=2),
        gap_analysis=json.dumps(gap_analysis, indent=2),
    )

    response = client.messages.create(
        model="claude-opus-4-6-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.content[0].text
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    return json.loads(content.strip())


def format_cover_letter_text(cl_data: dict) -> str:
    """Format cover letter data into plain text."""
    lines = [cl_data.get("salutation", "Dear Hiring Manager,"), ""]
    for para in cl_data.get("paragraphs", []):
        lines.append(para)
        lines.append("")
    lines.append(cl_data.get("sign_off", "Sincerely,"))
    lines.append(cl_data.get("candidate_name", ""))
    return "\n".join(lines)
