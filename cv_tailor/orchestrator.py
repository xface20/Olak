"""Main agentic orchestrator for the CV tailoring pipeline.

Pipeline stages:
1. EXTRACT  - Read CV (PDF) and Role Spec (URL/text) in parallel
2. ANALYZE  - Gap analysis between CV and role (Sonnet for speed)
3. REWRITE  - Rewrite CV aligned to role (Opus for quality)
4. COVER    - Generate tailored cover letter (Opus for quality)
5. RENDER   - Generate executive PDF output
"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable
from anthropic import Anthropic

from cv_tailor.agents.cv_reader import parse_cv
from cv_tailor.agents.role_reader import parse_role
from cv_tailor.agents.cv_rewriter import analyze_gaps, rewrite_cv
from cv_tailor.agents.cover_letter import generate_cover_letter, format_cover_letter_text
from cv_tailor.templates.executive_pdf import render_cv_pdf


def _log(stage: str, message: str):
    timestamp = time.strftime("%H:%M:%S")
    print(f"  [{timestamp}] [{stage}] {message}")


class PipelineResult:
    """Holds all outputs from the pipeline for use by CLI or UI."""

    def __init__(self):
        self.cv_raw_text: str = ""
        self.cv_structured: dict = {}
        self.role_structured: dict = {}
        self.gap_analysis: dict = {}
        self.rewritten_cv: dict = {}
        self.cover_letter: dict = {}
        self.cover_letter_text: str = ""
        self.output_pdf_path: str = ""
        self.alignment_score: int | str = "N/A"


def run_pipeline(
    cv_pdf_path: str,
    role_source: str,
    output_path: str | None = None,
    api_key: str | None = None,
    on_status: Callable[[str, str], None] | None = None,
) -> PipelineResult:
    """Run the full CV tailoring pipeline.

    Args:
        cv_pdf_path: Path to the input CV PDF.
        role_source: URL or free text of the role specification.
        output_path: Where to save the output PDF. Defaults to <cv_name>_tailored.pdf.
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
        on_status: Optional callback(stage, message) for UI progress updates.

    Returns:
        PipelineResult with all intermediate and final outputs.
    """
    result = PipelineResult()

    def status(stage: str, message: str):
        _log(stage, message)
        if on_status:
            on_status(stage, message)

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
    status("EXTRACT", "Reading CV and role specification in parallel...")

    cv_result = {}
    role_result = {}
    errors = []

    def _read_cv():
        nonlocal cv_result
        try:
            cv_result = parse_cv(cv_pdf_path, client)
            status("EXTRACT", f"CV parsed: {len(cv_result['raw_text'])} chars extracted")
        except Exception as e:
            errors.append(f"CV extraction failed: {e}")

    def _read_role():
        nonlocal role_result
        try:
            role_result = parse_role(role_source, client)
            role_title = role_result["structured"].get("job_title", "Unknown")
            status("EXTRACT", f"Role parsed: {role_title}")
        except Exception as e:
            errors.append(f"Role extraction failed: {e}")

    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(_read_cv)
        executor.submit(_read_role)

    if errors:
        for err in errors:
            status("ERROR", err)
        raise RuntimeError("Extraction stage failed: " + "; ".join(errors))

    result.cv_raw_text = cv_result["raw_text"]
    result.cv_structured = cv_result["structured"]
    result.role_structured = role_result["structured"]

    # -- Stage 2: Gap Analysis --
    status("ANALYZE", "Running gap analysis (Sonnet)...")
    gap_result = analyze_gaps(cv_result["structured"], role_result["structured"], client)
    result.gap_analysis = gap_result
    score = gap_result.get("alignment_score", "N/A")
    result.alignment_score = score
    status("ANALYZE", f"Alignment score: {score}/100")
    status("ANALYZE", f"Strong matches: {len(gap_result.get('strong_matches', []))}")
    status("ANALYZE", f"Gaps identified: {len(gap_result.get('gaps', []))}")
    status("ANALYZE", f"Reframing opportunities: {len(gap_result.get('reframing_opportunities', []))}")

    # -- Stage 3: CV Rewrite + Cover Letter in parallel --
    status("REWRITE", "Rewriting CV and generating cover letter (Opus)...")

    rewrite_error = []
    cover_error = []

    def _do_rewrite():
        try:
            result.rewritten_cv = rewrite_cv(
                cv_result["structured"], role_result["structured"], gap_result, client
            )
            status("REWRITE", "CV content rewritten and optimized")
        except Exception as e:
            rewrite_error.append(str(e))

    def _do_cover():
        try:
            result.cover_letter = generate_cover_letter(
                cv_result["structured"], role_result["structured"], gap_result, client
            )
            result.cover_letter_text = format_cover_letter_text(result.cover_letter)
            status("COVER", "Cover letter generated")
        except Exception as e:
            cover_error.append(str(e))

    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(_do_rewrite)
        executor.submit(_do_cover)

    if rewrite_error:
        raise RuntimeError("CV rewrite failed: " + "; ".join(rewrite_error))
    if cover_error:
        status("WARN", f"Cover letter generation failed: {'; '.join(cover_error)}")

    # -- Stage 4: PDF Rendering --
    status("RENDER", "Generating executive PDF...")
    final_path = render_cv_pdf(result.rewritten_cv, output_path)
    result.output_pdf_path = final_path
    status("RENDER", f"PDF saved to: {final_path}")

    # -- Summary --
    print("\n" + "-" * 60)
    status("DONE", "Pipeline complete!")
    print(f"  Input CV:      {cv_pdf_path}")
    print(f"  Target Role:   {role_result['structured'].get('job_title', 'N/A')} "
          f"at {role_result['structured'].get('company', 'N/A')}")
    print(f"  Alignment:     {score}/100")
    print(f"  Output:        {final_path}")
    print("-" * 60 + "\n")

    return result
