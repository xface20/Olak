"""Main agentic orchestrator for the CV tailoring pipeline.

Pipeline stages:
1. EXTRACT  - Read CV (PDF) and Role Spec (URL/text) in parallel
2. ANALYZE  - Gap analysis between CV and role (Sonnet for speed)
3. REWRITE  - Rewrite CV aligned to role (Opus for quality)
4. RENDER   - Generate executive PDF output
"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from anthropic import Anthropic

from cv_tailor.agents.cv_reader import parse_cv
from cv_tailor.agents.role_reader import parse_role
from cv_tailor.agents.cv_rewriter import analyze_gaps, rewrite_cv
from cv_tailor.templates.executive_pdf import render_cv_pdf


def _log(stage: str, message: str):
    timestamp = time.strftime("%H:%M:%S")
    print(f"  [{timestamp}] [{stage}] {message}")


def run_pipeline(
    cv_pdf_path: str,
    role_source: str,
    output_path: str | None = None,
    api_key: str | None = None,
) -> str:
    """Run the full CV tailoring pipeline.

    Args:
        cv_pdf_path: Path to the input CV PDF.
        role_source: URL or free text of the role specification.
        output_path: Where to save the output PDF. Defaults to <cv_name>_tailored.pdf.
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.

    Returns:
        Path to the generated PDF.
    """
    if not os.path.isfile(cv_pdf_path):
        raise FileNotFoundError(f"CV PDF not found: {cv_pdf_path}")

    if output_path is None:
        base = os.path.splitext(os.path.basename(cv_pdf_path))[0]
        output_path = os.path.join(os.path.dirname(cv_pdf_path) or ".", f"{base}_tailored.pdf")

    client = Anthropic(api_key=api_key) if api_key else Anthropic()

    print("\n" + "=" * 60)
    print("  CV TAILOR AGENT — Executive CV Pipeline")
    print("=" * 60)

    # -- Stage 1: Parallel extraction --
    _log("EXTRACT", "Reading CV and role specification in parallel...")

    cv_result = {}
    role_result = {}
    errors = []

    def _read_cv():
        nonlocal cv_result
        try:
            cv_result = parse_cv(cv_pdf_path, client)
            _log("EXTRACT", f"CV parsed: {len(cv_result['raw_text'])} chars extracted")
        except Exception as e:
            errors.append(f"CV extraction failed: {e}")

    def _read_role():
        nonlocal role_result
        try:
            role_result = parse_role(role_source, client)
            role_title = role_result["structured"].get("job_title", "Unknown")
            _log("EXTRACT", f"Role parsed: {role_title}")
        except Exception as e:
            errors.append(f"Role extraction failed: {e}")

    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(_read_cv)
        executor.submit(_read_role)

    if errors:
        for err in errors:
            _log("ERROR", err)
        raise RuntimeError("Extraction stage failed: " + "; ".join(errors))

    # -- Stage 2: Gap Analysis --
    _log("ANALYZE", "Running gap analysis (Sonnet)...")
    gap_result = analyze_gaps(cv_result["structured"], role_result["structured"], client)
    score = gap_result.get("alignment_score", "N/A")
    _log("ANALYZE", f"Alignment score: {score}/100")
    _log("ANALYZE", f"Strong matches: {len(gap_result.get('strong_matches', []))}")
    _log("ANALYZE", f"Gaps identified: {len(gap_result.get('gaps', []))}")
    _log("ANALYZE", f"Reframing opportunities: {len(gap_result.get('reframing_opportunities', []))}")

    # -- Stage 3: CV Rewrite --
    _log("REWRITE", "Rewriting CV with executive positioning (Opus)...")
    rewritten_cv = rewrite_cv(
        cv_result["structured"], role_result["structured"], gap_result, client
    )
    _log("REWRITE", "CV content rewritten and optimized")

    # -- Stage 4: PDF Rendering --
    _log("RENDER", "Generating executive PDF...")
    final_path = render_cv_pdf(rewritten_cv, output_path)
    _log("RENDER", f"PDF saved to: {final_path}")

    # -- Summary --
    print("\n" + "-" * 60)
    _log("DONE", "Pipeline complete!")
    print(f"  Input CV:      {cv_pdf_path}")
    print(f"  Target Role:   {role_result['structured'].get('job_title', 'N/A')} "
          f"at {role_result['structured'].get('company', 'N/A')}")
    print(f"  Alignment:     {score}/100")
    print(f"  Output:        {final_path}")
    print("-" * 60 + "\n")

    return final_path
