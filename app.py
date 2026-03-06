#!/usr/bin/env python3
"""NiceGUI web application for CV Tailor Agent."""

import asyncio
import os
import secrets
import shutil
import tempfile
import time
from pathlib import Path

from nicegui import ui, app, events

# Ensure imports work
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cv_tailor.orchestrator import run_pipeline, PipelineResult

UPLOAD_DIR = Path(tempfile.mkdtemp(prefix="cv_tailor_"))
OUTPUT_DIR = UPLOAD_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ─── Shared state per session ───
_sessions: dict[str, dict] = {}


def _get_state() -> dict:
    sid = app.storage.browser.get("_sid")
    if not sid:
        sid = str(time.time_ns())
        app.storage.browser["_sid"] = sid
    if sid not in _sessions:
        _sessions[sid] = {
            "cv_path": None,
            "cv_filename": None,
            "result": None,
        }
    return _sessions[sid]


# ─── Custom CSS ───
CUSTOM_CSS = """
<style>
:root {
    --navy: #1B2A4A;
    --accent: #2563EB;
    --accent-light: #3B82F6;
    --bg-main: #F1F5F9;
    --bg-card: #FFFFFF;
    --text-primary: #1E293B;
    --text-secondary: #64748B;
    --border: #E2E8F0;
    --success: #059669;
    --warning: #D97706;
}
body {
    background: var(--bg-main) !important;
}
.header-bar {
    background: linear-gradient(135deg, #1B2A4A 0%, #2563EB 100%);
}
.upload-zone {
    border: 2px dashed var(--border);
    border-radius: 12px;
    transition: all 0.2s;
    background: var(--bg-card);
}
.upload-zone:hover {
    border-color: var(--accent);
    background: #F8FAFC;
}
.status-line {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.8rem;
    color: var(--text-secondary);
    padding: 2px 0;
}
.stage-badge {
    display: inline-block;
    padding: 1px 8px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 0.7rem;
    margin-right: 6px;
}
.metric-card {
    background: var(--bg-card);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    border: 1px solid var(--border);
}
.metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: var(--navy);
}
.metric-label {
    font-size: 0.8rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.result-card {
    background: var(--bg-card);
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    border: 1px solid var(--border);
}
.cover-letter-box {
    white-space: pre-wrap;
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 0.95rem;
    line-height: 1.7;
    color: var(--text-primary);
    padding: 24px;
    background: #FFFEF7;
    border: 1px solid #E5E2D6;
    border-radius: 8px;
}
.nicegui-content { padding: 0 !important; }
</style>
"""

STAGE_COLORS = {
    "EXTRACT": "#6366F1",
    "ANALYZE": "#D97706",
    "REWRITE": "#2563EB",
    "COVER": "#7C3AED",
    "RENDER": "#059669",
    "DONE": "#059669",
    "ERROR": "#DC2626",
    "WARN": "#D97706",
}


@ui.page("/")
async def index():
    ui.add_head_html(CUSTOM_CSS)

    state = _get_state()

    # ─── Header ───
    with ui.element("div").classes("header-bar w-full py-4 px-8"):
        with ui.row().classes("w-full max-w-6xl mx-auto items-center justify-between"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("description", size="28px").classes("text-white")
                ui.label("CV Tailor Agent").classes("text-white text-xl font-bold tracking-wide")
            ui.label("Powered by Claude Opus / Sonnet / Haiku").classes(
                "text-blue-200 text-xs tracking-wide"
            )

    # ─── Main content ───
    with ui.column().classes("w-full max-w-6xl mx-auto px-6 py-8 gap-6"):

        # ── Input Section ──
        with ui.card().classes("w-full result-card").style("padding: 28px"):
            ui.label("Configure").classes("text-lg font-semibold text-slate-800 mb-4")

            with ui.row().classes("w-full gap-6 items-start"):

                # Left: Upload
                with ui.column().classes("flex-1 gap-3"):
                    ui.label("Upload CV (PDF)").classes("text-sm font-medium text-slate-600")
                    upload = ui.upload(
                        label="Drop your CV here or click to browse",
                        auto_upload=True,
                        max_file_size=10_000_000,
                        on_upload=lambda e: _handle_upload(e, file_label, state),
                    ).props('accept=".pdf" flat bordered').classes("w-full")
                    file_label = ui.label("No file selected").classes(
                        "text-xs text-slate-400"
                    )

                # Right: Role input
                with ui.column().classes("flex-1 gap-3"):
                    ui.label("Job Posting URL or Description").classes(
                        "text-sm font-medium text-slate-600"
                    )
                    role_input = ui.textarea(
                        placeholder="Paste a job posting URL (https://...) or type/paste the role description here...",
                    ).props("outlined rows=4").classes("w-full")

            # API Key (collapsible)
            with ui.expansion("API Key", icon="key").classes("w-full mt-2").props(
                "dense header-class='text-xs text-slate-400'"
            ):
                api_key_input = ui.input(
                    placeholder="sk-ant-... (or set ANTHROPIC_API_KEY env var)",
                ).props("outlined dense type=password").classes("w-full")

            # Action button
            with ui.row().classes("w-full justify-end mt-4"):
                run_btn = ui.button(
                    "Tailor My CV",
                    icon="auto_fix_high",
                    on_click=lambda: _run(
                        state, role_input, api_key_input, run_btn,
                        progress_container, results_container, log_container,
                        metrics_row,
                    ),
                ).props("unelevated color=primary size=lg").classes(
                    "px-8"
                ).style("background: linear-gradient(135deg, #1B2A4A, #2563EB) !important")

        # ── Progress Section ──
        progress_container = ui.column().classes("w-full gap-2")
        progress_container.set_visibility(False)

        # ── Metrics Row ──
        metrics_row = ui.row().classes("w-full gap-4")
        metrics_row.set_visibility(False)

        # ── Log ──
        log_container = ui.column().classes("w-full gap-0")
        log_container.set_visibility(False)

        # ── Results Section ──
        results_container = ui.column().classes("w-full gap-6")
        results_container.set_visibility(False)


def _handle_upload(e: events.UploadEventArguments, file_label: ui.label, state: dict):
    """Save uploaded file to temp dir."""
    dest = UPLOAD_DIR / e.name
    with open(dest, "wb") as f:
        f.write(e.content.read())
    state["cv_path"] = str(dest)
    state["cv_filename"] = e.name
    file_label.set_text(f"Uploaded: {e.name}")


async def _run(
    state, role_input, api_key_input, run_btn,
    progress_container, results_container, log_container, metrics_row,
):
    """Execute the pipeline with UI updates."""
    # Validate inputs
    cv_path = state.get("cv_path")
    if not cv_path:
        ui.notify("Please upload a CV PDF first", type="warning")
        return

    role_text = role_input.value
    if not role_text or not role_text.strip():
        ui.notify("Please enter a job posting URL or description", type="warning")
        return

    api_key = api_key_input.value if api_key_input.value else None

    # Prepare UI
    run_btn.disable()
    run_btn.props("loading")

    # Clear previous results
    results_container.clear()
    results_container.set_visibility(False)
    metrics_row.clear()
    metrics_row.set_visibility(False)
    log_container.clear()

    # Show progress
    progress_container.set_visibility(True)
    progress_container.clear()
    with progress_container:
        ui.label("Pipeline Running...").classes("text-sm font-semibold text-slate-700")
        spinner_row = ui.row().classes("items-center gap-2")
        with spinner_row:
            ui.spinner("dots", size="sm", color="primary")
            current_stage_label = ui.label("Starting...").classes("text-sm text-slate-500")
        progress_bar = ui.linear_progress(value=0, show_value=False).props(
            "color=primary rounded size=6px"
        ).classes("w-full")

    log_container.set_visibility(True)
    with log_container:
        with ui.card().classes("w-full result-card").style("padding: 16px"):
            ui.label("Agent Log").classes("text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2")
            log_column = ui.column().classes("w-full gap-0")

    stage_progress = {
        "EXTRACT": 0.15,
        "ANALYZE": 0.35,
        "REWRITE": 0.65,
        "COVER": 0.75,
        "RENDER": 0.90,
        "DONE": 1.0,
    }

    def on_status(stage: str, message: str):
        pval = stage_progress.get(stage, 0)
        progress_bar.set_value(pval)
        current_stage_label.set_text(f"{stage}: {message}")
        color = STAGE_COLORS.get(stage, "#64748B")
        with log_column:
            with ui.row().classes("items-center gap-1 status-line"):
                ui.html(
                    f'<span class="stage-badge" style="background:{color}20; color:{color}">{stage}</span>'
                )
                ui.label(message).classes("text-xs")

    # Run pipeline in background thread
    output_path = str(OUTPUT_DIR / f"{Path(cv_path).stem}_tailored.pdf")

    try:
        result: PipelineResult = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: run_pipeline(
                cv_pdf_path=cv_path,
                role_source=role_text,
                output_path=output_path,
                api_key=api_key,
                on_status=on_status,
            ),
        )
        state["result"] = result

        # Update progress to complete
        progress_bar.set_value(1.0)
        current_stage_label.set_text("Complete!")

        # Show metrics
        metrics_row.set_visibility(True)
        with metrics_row:
            _metric_card("Alignment Score", f"{result.alignment_score}%")
            _metric_card("Matches", str(len(result.gap_analysis.get("strong_matches", []))))
            _metric_card("Gaps Found", str(len(result.gap_analysis.get("gaps", []))))
            _metric_card("Reframes", str(len(result.gap_analysis.get("reframing_opportunities", []))))

        # Show results
        results_container.set_visibility(True)
        with results_container:
            _render_results(result)

        ui.notify("CV tailored successfully!", type="positive", position="top")

    except Exception as e:
        ui.notify(f"Pipeline error: {e}", type="negative", timeout=10000)
        on_status("ERROR", str(e))

    finally:
        run_btn.enable()
        run_btn.props(remove="loading")


def _metric_card(label: str, value: str):
    with ui.element("div").classes("flex-1 metric-card"):
        ui.label(value).classes("metric-value")
        ui.label(label).classes("metric-label mt-1")


def _render_results(result: PipelineResult):
    """Render the results section with tabs for CV, Cover Letter, and Analysis."""

    with ui.card().classes("w-full result-card").style("padding: 0; overflow: hidden"):
        with ui.tabs().classes("w-full").props("dense active-color=primary indicator-color=primary") as tabs:
            cv_tab = ui.tab("Tailored CV", icon="description")
            cl_tab = ui.tab("Cover Letter", icon="mail")
            analysis_tab = ui.tab("Gap Analysis", icon="analytics")

        with ui.tab_panels(tabs, value=cv_tab).classes("w-full").style("min-height: 500px"):

            # ── Tailored CV Panel ──
            with ui.tab_panel(cv_tab).classes("p-6"):
                with ui.row().classes("w-full justify-between items-center mb-4"):
                    ui.label("Tailored CV Preview").classes("text-lg font-semibold text-slate-800")
                    with ui.row().classes("gap-2"):
                        ui.button(
                            "Download PDF",
                            icon="download",
                            on_click=lambda: ui.download(result.output_pdf_path),
                        ).props("flat color=primary")

                _render_cv_preview(result.rewritten_cv)

            # ── Cover Letter Panel ──
            with ui.tab_panel(cl_tab).classes("p-6"):
                with ui.row().classes("w-full justify-between items-center mb-4"):
                    ui.label("Tailored Cover Letter").classes("text-lg font-semibold text-slate-800")
                    with ui.row().classes("gap-2"):
                        ui.button(
                            "Copy to Clipboard",
                            icon="content_copy",
                            on_click=lambda: ui.run_javascript(
                                f'navigator.clipboard.writeText({_js_string(result.cover_letter_text)})'
                            ),
                        ).props("flat color=primary")

                if result.cover_letter_text:
                    ui.element("div").classes("cover-letter-box w-full").props(
                        f'innerHTML="{_html_escape(result.cover_letter_text)}"'
                    )
                    # Also render as editable textarea
                    with ui.expansion("Edit Cover Letter", icon="edit").classes("w-full mt-4"):
                        ui.textarea(value=result.cover_letter_text).props(
                            "outlined rows=15"
                        ).classes("w-full font-serif")
                else:
                    ui.label("Cover letter generation was skipped or failed.").classes(
                        "text-slate-400 italic"
                    )

            # ── Gap Analysis Panel ──
            with ui.tab_panel(analysis_tab).classes("p-6"):
                ui.label("Gap Analysis Report").classes("text-lg font-semibold text-slate-800 mb-4")
                _render_gap_analysis(result.gap_analysis)


def _render_cv_preview(cv_data: dict):
    """Render the rewritten CV as styled HTML preview."""
    info = cv_data.get("personal_info", {})

    # Header
    with ui.column().classes("w-full items-center mb-4 pb-4").style(
        "border-bottom: 2px solid #1B2A4A"
    ):
        name = info.get("name", "")
        if name:
            ui.label(name).classes("text-2xl font-bold").style("color: #1B2A4A")
        title = info.get("title", "")
        if title:
            ui.label(title).classes("text-sm text-slate-500")
        contact_parts = [
            info.get(k) for k in ["email", "phone", "location", "linkedin"]
            if info.get(k)
        ]
        if contact_parts:
            ui.label(" | ".join(contact_parts)).classes("text-xs text-slate-400 mt-1")

    # Summary
    summary = cv_data.get("professional_summary", "")
    if summary:
        _section_header("Professional Summary")
        ui.label(summary).classes("text-sm text-slate-700 leading-relaxed")

    # Experience
    experience = cv_data.get("experience", [])
    if experience:
        _section_header("Professional Experience")
        for role in experience:
            with ui.row().classes("w-full justify-between items-start mt-3"):
                with ui.column().classes("gap-0"):
                    ui.label(role.get("company", "")).classes("text-sm font-bold text-slate-800")
                    ui.label(role.get("title", "")).classes("text-sm italic text-slate-500")
                with ui.column().classes("items-end gap-0"):
                    ui.label(role.get("dates", "")).classes("text-xs text-slate-400")
                    loc = role.get("location", "")
                    if loc:
                        ui.label(loc).classes("text-xs text-slate-400")
            for ach in role.get("achievements", []):
                with ui.row().classes("ml-4 mt-1 gap-2"):
                    ui.label("\u2022").classes("text-slate-400 text-sm")
                    ui.label(ach).classes("text-sm text-slate-700 leading-snug")

    # Skills
    skills = cv_data.get("skills", {})
    has_skills = any(v for v in skills.values() if isinstance(v, list) and v and v != [""])
    if has_skills:
        _section_header("Core Competencies")
        for cat, items in skills.items():
            if not items or items == [""]:
                continue
            label = cat.replace("_", " ").title()
            with ui.row().classes("gap-2 mt-1 items-start"):
                ui.label(f"{label}:").classes("text-xs font-bold text-slate-600 min-w-[120px]")
                ui.label(", ".join(i for i in items if i)).classes("text-xs text-slate-600")

    # Education
    education = cv_data.get("education", [])
    if education:
        _section_header("Education")
        for edu in education:
            with ui.row().classes("w-full justify-between items-start mt-2"):
                with ui.column().classes("gap-0"):
                    ui.label(edu.get("institution", "")).classes("text-sm font-bold text-slate-800")
                    ui.label(edu.get("degree", "")).classes("text-sm text-slate-600")
                ui.label(edu.get("dates", "")).classes("text-xs text-slate-400")


def _section_header(text: str):
    with ui.element("div").classes("w-full mt-5 mb-2 pb-1").style(
        "border-bottom: 1px solid #CBD5E1"
    ):
        ui.label(text.upper()).classes("text-xs font-bold tracking-widest").style(
            "color: #1B2A4A"
        )


def _render_gap_analysis(gap: dict):
    """Render gap analysis as structured cards."""
    if not gap:
        ui.label("No analysis data available.").classes("text-slate-400 italic")
        return

    # Strong matches
    matches = gap.get("strong_matches", [])
    if matches:
        with ui.expansion("Strong Matches", icon="check_circle").classes("w-full").props(
            "default-opened header-class='text-green-700 font-semibold'"
        ):
            for m in matches:
                with ui.row().classes("items-start gap-2 ml-2"):
                    ui.icon("check", size="16px").classes("text-green-500 mt-0.5")
                    ui.label(m).classes("text-sm text-slate-700")

    # Gaps
    gaps = gap.get("gaps", [])
    if gaps:
        with ui.expansion("Identified Gaps", icon="warning").classes("w-full").props(
            "header-class='text-amber-700 font-semibold'"
        ):
            for g in gaps:
                with ui.row().classes("items-start gap-2 ml-2"):
                    ui.icon("warning", size="16px").classes("text-amber-500 mt-0.5")
                    ui.label(g).classes("text-sm text-slate-700")

    # Reframing opportunities
    reframes = gap.get("reframing_opportunities", [])
    if reframes:
        with ui.expansion("Reframing Opportunities", icon="swap_horiz").classes("w-full").props(
            "header-class='text-blue-700 font-semibold'"
        ):
            for r in reframes:
                if isinstance(r, dict):
                    with ui.column().classes("ml-2 mb-2 gap-1"):
                        ui.label(f"Original: {r.get('original', '')}").classes(
                            "text-sm text-slate-500 italic"
                        )
                        ui.label(f"Suggestion: {r.get('suggestion', '')}").classes(
                            "text-sm text-blue-700 font-medium"
                        )

    # Strategic recommendations
    recs = gap.get("strategic_recommendations", [])
    if recs:
        with ui.expansion("Strategic Recommendations", icon="lightbulb").classes("w-full").props(
            "header-class='text-purple-700 font-semibold'"
        ):
            for r in recs:
                with ui.row().classes("items-start gap-2 ml-2"):
                    ui.icon("lightbulb", size="16px").classes("text-purple-400 mt-0.5")
                    ui.label(r).classes("text-sm text-slate-700")


def _html_escape(text: str) -> str:
    """Escape for safe insertion into innerHTML."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("\n", "<br>")
    )


def _js_string(text: str) -> str:
    """Escape a Python string for safe use in JavaScript."""
    return (
        "'"
        + text.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        + "'"
    )


# ─── Serve uploaded PDFs for download ───
app.add_static_files("/output", str(OUTPUT_DIR))

ui.run(
    title="CV Tailor Agent",
    port=int(os.environ.get("PORT", 8081)),
    reload=False,
    storage_secret="cv_tailor_secret_key_change_me",
)
