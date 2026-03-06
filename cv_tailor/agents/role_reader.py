"""Agent for extracting role specifications from URLs or free text."""

import requests
from bs4 import BeautifulSoup
from anthropic import Anthropic

ROLE_EXTRACTION_PROMPT = """You are an expert job specification analyst. Extract and structure the role requirements from the following text.

Return a JSON object:
{
  "job_title": "",
  "company": "",
  "location": "",
  "seniority_level": "",
  "department": "",
  "key_responsibilities": [""],
  "required_skills": [""],
  "preferred_skills": [""],
  "required_experience": "",
  "education_requirements": "",
  "key_competencies": [""],
  "industry_keywords": [""],
  "culture_values": [""],
  "reporting_to": "",
  "team_size": ""
}

Extract every detail. For industry_keywords, identify the domain-specific terms and buzzwords that would make a CV stand out for this role.

Role Text:
"""


def fetch_url_content(url: str) -> str:
    """Fetch and extract readable text from a URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove scripts, styles, navs, footers
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    # Collapse whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def parse_role(source: str, client: Anthropic) -> dict:
    """Parse role specification from a URL or free text.

    Uses Claude Haiku for fast extraction.
    """
    # Determine if source is a URL
    if source.strip().startswith(("http://", "https://")):
        role_text = fetch_url_content(source.strip())
    else:
        role_text = source

    if not role_text.strip():
        raise ValueError("No role specification text provided")

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": ROLE_EXTRACTION_PROMPT + role_text,
            }
        ],
    )

    import json
    content = response.content[0].text
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    return {"raw_text": role_text, "structured": json.loads(content.strip())}
