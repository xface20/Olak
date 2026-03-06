"""Executive CV PDF template using ReportLab.

Produces a clean, modern executive-style CV with:
- Elegant typography and spacing
- Navy/dark accent color scheme
- Clear section hierarchy with subtle dividers
- Professional layout optimized for readability and ATS
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# -- Color Palette --
NAVY = HexColor("#1B2A4A")
DARK_GRAY = HexColor("#2D3436")
MID_GRAY = HexColor("#636E72")
LIGHT_GRAY = HexColor("#B2BEC3")
ACCENT = HexColor("#1B2A4A")
WHITE = HexColor("#FFFFFF")
SUBTLE_BG = HexColor("#F8F9FA")
DIVIDER_COLOR = HexColor("#CBD5E1")
GOLD_ACCENT = HexColor("#B8860B")


def _register_fonts():
    """Register available system fonts, fallback to Helvetica."""
    font_dirs = [
        "/usr/share/fonts/truetype/dejavu/",
        "/usr/share/fonts/truetype/liberation/",
    ]
    for d in font_dirs:
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith(".ttf"):
                    name = f.replace(".ttf", "")
                    try:
                        pdfmetrics.registerFont(TTFont(name, os.path.join(d, f)))
                    except Exception:
                        pass


_register_fonts()

# Font selection — prefer Liberation, fallback to Helvetica
_SERIF = "Helvetica"
_SERIF_BOLD = "Helvetica-Bold"
_SERIF_ITALIC = "Helvetica-Oblique"
_SANS = "Helvetica"
_SANS_BOLD = "Helvetica-Bold"

for name in ["LiberationSans-Regular", "DejaVuSans"]:
    if name in pdfmetrics.getRegisteredFontNames():
        _SANS = name
        break
for name in ["LiberationSans-Bold", "DejaVuSans-Bold"]:
    if name in pdfmetrics.getRegisteredFontNames():
        _SANS_BOLD = name
        break
for name in ["LiberationSerif-Regular", "DejaVuSerif"]:
    if name in pdfmetrics.getRegisteredFontNames():
        _SERIF = name
        break
for name in ["LiberationSerif-Bold", "DejaVuSerif-Bold"]:
    if name in pdfmetrics.getRegisteredFontNames():
        _SERIF_BOLD = name
        break
for name in ["LiberationSerif-Italic", "DejaVuSerif-Italic"]:
    if name in pdfmetrics.getRegisteredFontNames():
        _SERIF_ITALIC = name
        break


# -- Styles --
def _styles():
    return {
        "name": ParagraphStyle(
            "Name",
            fontName=_SANS_BOLD,
            fontSize=22,
            leading=28,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=2 * mm,
        ),
        "title": ParagraphStyle(
            "Title",
            fontName=_SANS,
            fontSize=11,
            leading=14,
            textColor=MID_GRAY,
            alignment=TA_CENTER,
            spaceAfter=2 * mm,
        ),
        "contact": ParagraphStyle(
            "Contact",
            fontName=_SANS,
            fontSize=8.5,
            leading=12,
            textColor=MID_GRAY,
            alignment=TA_CENTER,
            spaceAfter=4 * mm,
        ),
        "section_heading": ParagraphStyle(
            "SectionHeading",
            fontName=_SANS_BOLD,
            fontSize=11,
            leading=14,
            textColor=NAVY,
            spaceBefore=6 * mm,
            spaceAfter=2 * mm,
            textTransform="uppercase",
            letterSpacing=1.5,
        ),
        "company": ParagraphStyle(
            "Company",
            fontName=_SANS_BOLD,
            fontSize=10,
            leading=13,
            textColor=DARK_GRAY,
            spaceBefore=3 * mm,
        ),
        "role_title": ParagraphStyle(
            "RoleTitle",
            fontName=_SERIF_ITALIC,
            fontSize=9.5,
            leading=12,
            textColor=MID_GRAY,
        ),
        "dates": ParagraphStyle(
            "Dates",
            fontName=_SANS,
            fontSize=8.5,
            leading=11,
            textColor=MID_GRAY,
            alignment=TA_LEFT,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            fontName=_SERIF,
            fontSize=9.5,
            leading=13,
            textColor=DARK_GRAY,
            leftIndent=10 * mm,
            bulletIndent=4 * mm,
            spaceBefore=1 * mm,
            alignment=TA_JUSTIFY,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName=_SERIF,
            fontSize=9.5,
            leading=13.5,
            textColor=DARK_GRAY,
            alignment=TA_JUSTIFY,
            spaceAfter=2 * mm,
        ),
        "skill_category": ParagraphStyle(
            "SkillCategory",
            fontName=_SANS_BOLD,
            fontSize=9,
            leading=12,
            textColor=NAVY,
        ),
        "skill_items": ParagraphStyle(
            "SkillItems",
            fontName=_SERIF,
            fontSize=9,
            leading=12,
            textColor=DARK_GRAY,
        ),
        "education_inst": ParagraphStyle(
            "EduInst",
            fontName=_SANS_BOLD,
            fontSize=9.5,
            leading=12,
            textColor=DARK_GRAY,
            spaceBefore=2 * mm,
        ),
        "education_detail": ParagraphStyle(
            "EduDetail",
            fontName=_SERIF,
            fontSize=9,
            leading=12,
            textColor=MID_GRAY,
        ),
    }


def _section_divider():
    return HRFlowable(
        width="100%",
        thickness=0.5,
        color=DIVIDER_COLOR,
        spaceBefore=1 * mm,
        spaceAfter=1 * mm,
    )


def _escape(text: str) -> str:
    """Escape XML special characters for ReportLab Paragraphs."""
    if not text:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def render_cv_pdf(cv_data: dict, output_path: str) -> str:
    """Render structured CV data to an executive-style PDF.

    Args:
        cv_data: Structured CV dictionary from the rewriter agent.
        output_path: Where to save the PDF.

    Returns:
        The output file path.
    """
    styles = _styles()
    story = []

    # -- Header: Name --
    info = cv_data.get("personal_info", {})
    name = info.get("name", "")
    if name:
        story.append(Paragraph(_escape(name), styles["name"]))

    # -- Title --
    title = info.get("title", "")
    if title:
        story.append(Paragraph(_escape(title), styles["title"]))

    # -- Contact line --
    contact_parts = []
    for key in ["email", "phone", "location", "linkedin", "website"]:
        val = info.get(key)
        if val:
            contact_parts.append(_escape(val))
    if contact_parts:
        contact_line = "  &bull;  ".join(contact_parts)  # noqa: RUF001
        story.append(Paragraph(contact_line, styles["contact"]))

    story.append(_section_divider())

    # -- Professional Summary --
    summary = cv_data.get("professional_summary", "")
    if summary:
        story.append(
            Paragraph(_escape("PROFESSIONAL SUMMARY"), styles["section_heading"])
        )
        story.append(Paragraph(_escape(summary), styles["body"]))
        story.append(_section_divider())

    # -- Experience --
    experience = cv_data.get("experience", [])
    if experience:
        story.append(
            Paragraph(_escape("PROFESSIONAL EXPERIENCE"), styles["section_heading"])
        )
        story.append(_section_divider())

        for role in experience:
            # Company + Dates on one line via table
            company_text = _escape(role.get("company", ""))
            dates_text = _escape(role.get("dates", ""))
            location_text = _escape(role.get("location", ""))

            left_content = f"<b>{company_text}</b>"
            if location_text:
                left_content += f"  |  {location_text}"

            header_table = Table(
                [
                    [
                        Paragraph(left_content, styles["company"]),
                        Paragraph(dates_text, styles["dates"]),
                    ]
                ],
                colWidths=["70%", "30%"],
            )
            header_table.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (0, 0), "LEFT"),
                        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            story.append(header_table)

            role_title = role.get("title", "")
            if role_title:
                story.append(Paragraph(_escape(role_title), styles["role_title"]))

            for achievement in role.get("achievements", []):
                bullet_text = f"&bull;  {_escape(achievement)}"  # noqa: RUF001
                story.append(Paragraph(bullet_text, styles["bullet"]))

            story.append(Spacer(1, 2 * mm))

    # -- Skills --
    skills = cv_data.get("skills", {})
    has_skills = any(
        v for v in skills.values() if isinstance(v, list) and v and v != [""]
    )
    if has_skills:
        story.append(Paragraph(_escape("CORE COMPETENCIES"), styles["section_heading"]))
        story.append(_section_divider())

        for category, items in skills.items():
            if not items or items == [""]:
                continue
            label = category.replace("_", " ").title()
            items_text = ", ".join(_escape(i) for i in items if i)
            if items_text:
                row = Table(
                    [
                        [
                            Paragraph(_escape(label) + ":", styles["skill_category"]),
                            Paragraph(items_text, styles["skill_items"]),
                        ]
                    ],
                    colWidths=[35 * mm, None],
                )
                row.setStyle(
                    TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ("TOPPADDING", (0, 0), (-1, -1), 1),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                        ]
                    )
                )
                story.append(row)

        story.append(Spacer(1, 2 * mm))

    # -- Education --
    education = cv_data.get("education", [])
    if education:
        story.append(Paragraph(_escape("EDUCATION"), styles["section_heading"]))
        story.append(_section_divider())

        for edu in education:
            inst = _escape(edu.get("institution", ""))
            degree = _escape(edu.get("degree", ""))
            dates = _escape(edu.get("dates", ""))
            details = _escape(edu.get("details", ""))

            edu_header = Table(
                [
                    [
                        Paragraph(f"<b>{inst}</b>", styles["education_inst"]),
                        Paragraph(dates, styles["dates"]),
                    ]
                ],
                colWidths=["70%", "30%"],
            )
            edu_header.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            story.append(edu_header)

            if degree:
                story.append(Paragraph(degree, styles["education_detail"]))
            if details:
                story.append(Paragraph(details, styles["education_detail"]))

    # -- Additional sections --
    additional = cv_data.get("additional_sections", {})
    if additional:
        for section_name, section_content in additional.items():
            label = section_name.replace("_", " ").title()
            story.append(Paragraph(_escape(label), styles["section_heading"]))
            story.append(_section_divider())
            if isinstance(section_content, list):
                for item in section_content:
                    story.append(
                        Paragraph(f"&bull;  {_escape(item)}", styles["bullet"])  # noqa: RUF001
                    )
            elif isinstance(section_content, str):
                story.append(Paragraph(_escape(section_content), styles["body"]))

    # -- Build PDF --
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title=f"CV - {name}",
        author="CV Tailor Agent",
    )
    doc.build(story)
    return output_path
