"""Agent for analyzing CV against role requirements and rewriting to align."""

import json
from anthropic import Anthropic

GAP_ANALYSIS_PROMPT = """You are a senior executive career strategist and CV optimization expert.

Analyze this CV against the target role requirements. Identify:
1. ALIGNMENT: Skills, experiences, and achievements that directly match role requirements
2. GAPS: Required skills or experiences missing from the CV
3. REFRAMING OPPORTUNITIES: Existing experiences that can be reworded to better align
4. KEYWORD GAPS: Industry terms from the role spec not present in the CV
5. IMPACT METRICS: Where to strengthen quantified achievements

Return a JSON object:
{
  "alignment_score": 0-100,
  "strong_matches": [""],
  "gaps": [""],
  "reframing_opportunities": [{"original": "", "suggestion": ""}],
  "keyword_gaps": [""],
  "metric_opportunities": [""],
  "strategic_recommendations": [""]
}

CV Data:
{cv_data}

Role Requirements:
{role_data}
"""

REWRITE_PROMPT = """You are a world-class executive CV writer who crafts compelling, ATS-optimized resumes for senior professionals.

Using the gap analysis and original CV data, rewrite the CV to maximally align with the target role.

RULES:
- NEVER fabricate experience, skills, or qualifications not present in the original CV
- DO reframe and reword existing experiences to highlight relevance to the target role
- DO incorporate industry keywords naturally where the candidate has genuine experience
- DO strengthen achievement statements with the STAR method (Situation, Task, Action, Result)
- DO prioritize experiences most relevant to the target role
- DO write a powerful executive summary tailored to this specific role
- DO use strong action verbs and quantified achievements
- Keep the professional summary to 3-4 impactful sentences
- Each role should have 3-5 bullet points, prioritized by relevance to target role
- Skills section should lead with skills matching the role requirements

Return a JSON object with the rewritten CV:
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
    "core_competencies": [""],
    "technical_skills": [""],
    "certifications": [""],
    "languages": [""]
  },
  "additional_sections": {}
}

Original CV Data:
{cv_data}

Role Requirements:
{role_data}

Gap Analysis:
{gap_analysis}
"""


def analyze_gaps(cv_data: dict, role_data: dict, client: Anthropic) -> dict:
    """Analyze gaps between CV and role requirements using Opus for deep reasoning."""
    prompt = GAP_ANALYSIS_PROMPT.format(
        cv_data=json.dumps(cv_data, indent=2),
        role_data=json.dumps(role_data, indent=2),
    )

    response = client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.content[0].text
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    return json.loads(content.strip())


def rewrite_cv(
    cv_data: dict, role_data: dict, gap_analysis: dict, client: Anthropic
) -> dict:
    """Rewrite CV to align with role requirements using Opus for best quality."""
    prompt = REWRITE_PROMPT.format(
        cv_data=json.dumps(cv_data, indent=2),
        role_data=json.dumps(role_data, indent=2),
        gap_analysis=json.dumps(gap_analysis, indent=2),
    )

    response = client.messages.create(
        model="claude-opus-4-6-20250514",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.content[0].text
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    return json.loads(content.strip())
