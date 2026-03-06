#!/usr/bin/env python3
"""CLI entry point for the CV Tailor Agent.

Usage:
    python run.py <cv.pdf> <role_url_or_text> [output.pdf]

Examples:
    # With a job posting URL:
    python run.py my_cv.pdf "https://example.com/job-posting"

    # With free text role description:
    python run.py my_cv.pdf "Senior Product Manager at TechCo. Requirements: 8+ years PM experience, SaaS, Agile..."

    # With custom output path:
    python run.py my_cv.pdf "https://example.com/job" tailored_cv.pdf
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cv_tailor.orchestrator import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="CV Tailor Agent — Align your CV with any role specification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Model usage:
  - Haiku 4.5   : CV parsing, role extraction (fast structured extraction)
  - Sonnet 4.6  : Gap analysis (balanced speed + reasoning)
  - Opus 4.6    : CV rewriting (highest quality output)
  - ReportLab   : Executive PDF rendering

Set ANTHROPIC_API_KEY environment variable or pass --api-key.
        """,
    )
    parser.add_argument("cv_pdf", help="Path to input CV in PDF format")
    parser.add_argument(
        "role",
        help="Role specification: URL to a job posting, or free text description",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="Output PDF path (default: <cv_name>_tailored.pdf)",
    )
    parser.add_argument("--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY)")

    args = parser.parse_args()

    try:
        result = run_pipeline(
            cv_pdf_path=args.cv_pdf,
            role_source=args.role,
            output_path=args.output,
            api_key=args.api_key,
        )
        print(f"Success! Tailored CV saved to: {result}")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
