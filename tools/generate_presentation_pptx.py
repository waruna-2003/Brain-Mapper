"""
Generate the Brain Mapper Progress & Proposal Presentation (.pptx)
following the 9-section presentation structure and refined proposal content.
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_PPTX = PROJECT_ROOT / "docs" / "Brain_Mapper_Progress_Presentation.pptx"
DIAGRAMS_DIR = PROJECT_ROOT / "docs" / "diagrams"
UI_ARCH_IMG = Path(
    r"C:\Users\USER\.gemini\antigravity\brain\d12d1dca-c876-44b5-93cb-9429de5cb0a1\brainmapper_ui_architecture_v2_1794300376305.jpg"
)

# Color Palette (BrainMapper Brand Theme)
C_DARK_NAVY = RGBColor(0x1E, 0x1B, 0x4B)
C_INDIGO = RGBColor(0x4F, 0x46, 0xE5)
C_VIOLET = RGBColor(0x7C, 0x3A, 0xED)
C_PURPLE_SOFT = RGBColor(0xED, 0xE9, 0xFE)
C_INDIGO_SOFT = RGBColor(0xEE, 0xF2, 0xFF)
C_TEAL = RGBColor(0x0D, 0x94, 0x88)
C_TEAL_SOFT = RGBColor(0xCC, 0xFB, 0xF1)
C_EMERALD = RGBColor(0x05, 0x96, 0x69)
C_EMERALD_SOFT = RGBColor(0xD1, 0xFA, 0xE5)
C_AMBER = RGBColor(0xD9, 0x77, 0x06)
C_AMBER_SOFT = RGBColor(0xFE, 0xF3, 0xC7)
C_ROSE = RGBColor(0xE1, 0x1D, 0x48)
C_ROSE_SOFT = RGBColor(0xFF, 0xE4, 0xE6)
C_BLUE = RGBColor(0x25, 0x63, 0xEB)
C_BLUE_SOFT = RGBColor(0xDB, 0xEA, 0xFE)
C_BG_LIGHT = RGBColor(0xF8, 0xFA, 0xFC)
C_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
C_BORDER = RGBColor(0xCB, 0xD5, 0xE1)
C_TEXT_DARK = RGBColor(0x1E, 0x29, 0x3B)
C_TEXT_MUTED = RGBColor(0x47, 0x55, 0x69)
C_TEXT_LIGHT = RGBColor(0x94, 0xA3, 0xB8)


def set_bg(slide, color: RGBColor) -> None:
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_header(
    slide,
    section_num: str,
    section_label: str,
    title: str,
    accent: RGBColor = C_INDIGO,
    slide_no: int = 1,
    total_slides: int = 14,
) -> None:
    set_bg(slide, C_BG_LIGHT)

    # Top accent bar
    top_bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.12)
    )
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = accent
    top_bar.line.fill.background()

    # Section pill badge
    pill = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(0.32), Inches(2.55), Inches(0.36)
    )
    pill.fill.solid()
    pill.fill.fore_color.rgb = accent
    pill.line.fill.background()
    tf = pill.text_frame
    tf.word_wrap = False
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = f"{section_num}  |  {section_label.upper()}"
    r.font.name = "Calibri"
    r.font.size = Pt(10.5)
    r.font.bold = True
    r.font.color.rgb = C_WHITE

    # Slide title
    tbox = slide.shapes.add_textbox(Inches(0.6), Inches(0.72), Inches(12.1), Inches(0.6))
    ttf = tbox.text_frame
    ttf.word_wrap = True
    ttf.margin_left = 0
    ttf.margin_top = 0
    tp = ttf.paragraphs[0]
    tr = tp.add_run()
    tr.text = title
    tr.font.name = "Calibri"
    tr.font.size = Pt(25)
    tr.font.bold = True
    tr.font.color.rgb = C_DARK_NAVY

    # Thin divider
    div = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(1.36), Inches(12.133), Inches(0.02)
    )
    div.fill.solid()
    div.fill.fore_color.rgb = C_BORDER
    div.line.fill.background()

    # Footer
    fbox = slide.shapes.add_textbox(Inches(0.6), Inches(7.12), Inches(9.0), Inches(0.28))
    fp = fbox.text_frame.paragraphs[0]
    fr = fp.add_run()
    fr.text = "Brain Mapper  |  Cognitive-Aware Learning Analytics Framework  |  SLTC Research University"
    fr.font.name = "Calibri"
    fr.font.size = Pt(9.5)
    fr.font.color.rgb = C_TEXT_LIGHT

    nbox = slide.shapes.add_textbox(Inches(11.4), Inches(7.12), Inches(1.333), Inches(0.28))
    np_ = nbox.text_frame.paragraphs[0]
    np_.alignment = PP_ALIGN.RIGHT
    nr = np_.add_run()
    nr.text = f"{slide_no} / {total_slides}"
    nr.font.name = "Calibri"
    nr.font.size = Pt(9.5)
    nr.font.bold = True
    nr.font.color.rgb = accent


def add_card(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    title: str = "",
    accent: RGBColor = C_INDIGO,
    bg_color: RGBColor = C_WHITE,
    border_color: RGBColor = C_BORDER,
):
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    card.adjustments[0] = 0.04
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = border_color
    card.line.width = Pt(1.0)

    if title:
        # Left or top accent header strip inside card
        bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(left + 0.18), Inches(top + 0.16), Inches(0.08), Inches(0.32)
        )
        bar.fill.solid()
        bar.fill.fore_color.rgb = accent
        bar.line.fill.background()

        tb = slide.shapes.add_textbox(
            Inches(left + 0.34), Inches(top + 0.12), Inches(width - 0.5), Inches(0.4)
        )
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = 0
        tf.margin_top = 2
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = title
        r.font.name = "Calibri"
        r.font.size = Pt(14.5)
        r.font.bold = True
        r.font.color.rgb = C_DARK_NAVY
    return card


def add_bullets(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    items: list[tuple[str, str]],
    font_size: float = 12.0,
    space_after: float = 6.0,
) -> None:
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 4
    tf.margin_top = 0

    for idx, (lead, body) in enumerate(items):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.space_after = Pt(space_after)
        p.line_spacing = 1.15
        if lead:
            r1 = p.add_run()
            r1.text = f"• {lead}: " if body else f"• {lead}"
            r1.font.name = "Calibri"
            r1.font.size = Pt(font_size)
            r1.font.bold = True
            r1.font.color.rgb = C_DARK_NAVY
        if body:
            r2 = p.add_run()
            r2.text = body if lead else f"• {body}"
            r2.font.name = "Calibri"
            r2.font.size = Pt(font_size)
            r2.font.color.rgb = C_TEXT_DARK


def add_kpi_card(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    value: str,
    label: str,
    sublabel: str,
    accent: RGBColor,
    bg_soft: RGBColor,
) -> None:
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    card.adjustments[0] = 0.08
    card.fill.solid()
    card.fill.fore_color.rgb = bg_soft
    card.line.color.rgb = accent
    card.line.width = Pt(1.25)

    tb = slide.shapes.add_textbox(Inches(left + 0.14), Inches(top + 0.12), Inches(width - 0.28), Inches(height - 0.2))
    tf = tb.text_frame
    tf.word_wrap = True

    p1 = tf.paragraphs[0]
    p1.alignment = PP_ALIGN.CENTER
    r1 = p1.add_run()
    r1.text = value
    r1.font.name = "Calibri"
    r1.font.size = Pt(24)
    r1.font.bold = True
    r1.font.color.rgb = accent

    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    p2.space_before = Pt(2)
    r2 = p2.add_run()
    r2.text = label
    r2.font.name = "Calibri"
    r2.font.size = Pt(11.5)
    r2.font.bold = True
    r2.font.color.rgb = C_DARK_NAVY

    if sublabel:
        p3 = tf.add_paragraph()
        p3.alignment = PP_ALIGN.CENTER
        r3 = p3.add_run()
        r3.text = sublabel
        r3.font.name = "Calibri"
        r3.font.size = Pt(9.5)
        r3.font.color.rgb = C_TEXT_MUTED


def style_table(table, col_widths: list[float], header_bg: RGBColor = C_INDIGO, font_size: float = 10.5) -> None:
    for j, w in enumerate(col_widths):
        table.columns[j].width = Inches(w)

    for i, row in enumerate(table.rows):
        for j, cell in enumerate(row.cells):
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = Inches(0.08)
            cell.margin_right = Inches(0.08)
            cell.margin_top = Inches(0.05)
            cell.margin_bottom = Inches(0.05)
            fill = cell.fill
            fill.solid()
            if i == 0:
                fill.fore_color.rgb = header_bg
            elif i % 2 == 1:
                fill.fore_color.rgb = C_WHITE
            else:
                fill.fore_color.rgb = RGBColor(0xF1, 0xF5, 0xF9)

            for p in cell.text_frame.paragraphs:
                p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
                for r in p.runs:
                    r.font.name = "Calibri"
                    r.font.size = Pt(font_size)
                    if i == 0:
                        r.font.bold = True
                        r.font.color.rgb = C_WHITE
                    else:
                        r.font.color.rgb = C_TEXT_DARK


def build_presentation() -> None:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]
    total_slides = 14

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_bg(s1, C_DARK_NAVY)

    # Decorative geometric accent bands
    band1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.32), Inches(7.5))
    band1.fill.solid()
    band1.fill.fore_color.rgb = C_INDIGO
    band1.line.fill.background()

    band2 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.32), Inches(0), Inches(0.10), Inches(7.5))
    band2.fill.solid()
    band2.fill.fore_color.rgb = C_TEAL
    band2.line.fill.background()

    # Decorative circle glow top-right
    circ = s1.shapes.add_shape(MSO_SHAPE.OVAL, Inches(10.6), Inches(-1.2), Inches(4.0), Inches(4.0))
    circ.fill.solid()
    circ.fill.fore_color.rgb = RGBColor(0x31, 0x2E, 0x81)
    circ.line.fill.background()

    # Badge
    badge = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.95), Inches(0.85), Inches(4.3), Inches(0.42))
    badge.fill.solid()
    badge.fill.fore_color.rgb = C_TEAL
    badge.line.fill.background()
    bp = badge.text_frame.paragraphs[0]
    bp.alignment = PP_ALIGN.CENTER
    br = bp.add_run()
    br.text = "BRAIN MAPPER  |  PROGRESS PRESENTATION"
    br.font.name = "Calibri"
    br.font.size = Pt(11.5)
    br.font.bold = True
    br.font.color.rgb = C_WHITE

    # Title
    t1 = s1.shapes.add_textbox(Inches(0.95), Inches(1.55), Inches(11.4), Inches(1.65))
    tf1 = t1.text_frame
    tf1.word_wrap = True
    p_title = tf1.paragraphs[0]
    r_title = p_title.add_run()
    r_title.text = "A Cognitive-Aware Learning Analytics Framework Using Large Language Models and Knowledge Tracing"
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(34)
    r_title.font.bold = True
    r_title.font.color.rgb = C_WHITE

    p_sub = tf1.add_paragraph()
    p_sub.space_before = Pt(10)
    r_sub = p_sub.add_run()
    r_sub.text = "Integrating 6-Dimensional LLM Cognitive Skill Extraction, CA-KT Modeling, and Offline LAN Assessment"
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(16)
    r_sub.font.color.rgb = RGBColor(0xC7, 0xD2, 0xFE)

    # Team & Supervisors Card
    team_card = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.95), Inches(4.15), Inches(11.45), Inches(2.55))
    team_card.adjustments[0] = 0.05
    team_card.fill.solid()
    team_card.fill.fore_color.rgb = RGBColor(0x28, 0x24, 0x62)
    team_card.line.color.rgb = C_INDIGO
    team_card.line.width = Pt(1.2)

    tb_team = s1.shapes.add_textbox(Inches(1.25), Inches(4.35), Inches(5.6), Inches(2.15))
    ttf = tb_team.text_frame
    ttf.word_wrap = True
    p0 = ttf.paragraphs[0]
    r0 = p0.add_run()
    r0.text = "RESEARCH TEAM (DEPARTMENT OF DATA SCIENCE)"
    r0.font.name = "Calibri"
    r0.font.size = Pt(11)
    r0.font.bold = True
    r0.font.color.rgb = C_TEAL_SOFT

    for member in [
        "• L. Waruna Lakshan Silva (Team Leader)",
        "• K.A.A. Dilshan",
        "• K.A. Pramudi Biyonika Himaranshi",
        "• Tharindu Kothlawala",
    ]:
        pm = ttf.add_paragraph()
        pm.space_before = Pt(4)
        rm = pm.add_run()
        rm.text = member
        rm.font.name = "Calibri"
        rm.font.size = Pt(13.5)
        rm.font.color.rgb = C_WHITE

    tb_sup = s1.shapes.add_textbox(Inches(7.1), Inches(4.35), Inches(5.0), Inches(2.15))
    stf = tb_sup.text_frame
    stf.word_wrap = True
    ps0 = stf.paragraphs[0]
    rs0 = ps0.add_run()
    rs0.text = "SUPERVISION & INSTITUTION"
    rs0.font.name = "Calibri"
    rs0.font.size = Pt(11)
    rs0.font.bold = True
    rs0.font.color.rgb = C_AMBER_SOFT

    for line in [
        "• Miss. Risuni Siyara (Dept. of Software Engineering)",
        "• Dr. Chameera De Silva (Dept. of Data Science)",
        "",
        "SLTC Research University, Ingiriya Road, Meepe, Sri Lanka",
    ]:
        ps = stf.add_paragraph()
        ps.space_before = Pt(4)
        rs = ps.add_run()
        rs.text = line
        rs.font.name = "Calibri"
        rs.font.size = Pt(13)
        rs.font.color.rgb = C_WHITE if line.startswith("•") else RGBColor(0xC7, 0xD2, 0xFE)

    # =========================================================================
    # SLIDE 2: 1. INTRODUCTION — OVERVIEW & PROBLEM STATEMENT
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "01", "Introduction", "Project Overview & Problem Statement", C_INDIGO, 2, total_slides)

    # Left Card: Overview
    add_card(s2, 0.6, 1.55, 5.9, 3.3, "Project Overview", C_INDIGO)
    add_bullets(
        s2, 0.85, 2.15, 5.4, 2.55,
        [
            ("Context", "In Sri Lankan schools, exam marks are mainly used for grading, leaving rich question-level answer script insights underutilized."),
            ("Brain Mapper Vision", "A Cognitive-Aware Learning Analytics Framework combining Large Language Models (LLMs) and Knowledge Tracing (KT)."),
            ("Core Mechanism", "Automatically scores 6 cognitive skills per question and integrates them with student response histories for accurate prediction & explainable learner profiles."),
            ("Real-World Delivery", "Paired with an offline LAN Digital Examination Platform to capture Grade 10–11 responses without internet access."),
        ],
        font_size=12.0,
    )

    # Right Card: Problem Statement
    add_card(s2, 6.8, 1.55, 5.93, 3.3, "Problem Definition", C_ROSE)
    add_bullets(
        s2, 7.05, 2.15, 5.45, 2.55,
        [
            ("Black-Box KT", "Traditional KT (DKT, qDKT, QKT) models correctness and concept IDs but ignores underlying cognitive processes."),
            ("Assessment Blind Spots", "Educators cannot tell why a student struggles (e.g., weak Working Memory vs. Logical Reasoning) or align exam difficulty."),
            ("Manual Bottleneck", "Expert cognitive tagging (Q-matrix / CDM) is slow, subjective, and impossible to scale to thousands of questions."),
            ("Data & Connectivity Gap", "Paper scripts are returned and lost by students; rural/school labs lack reliable internet for online testing."),
        ],
        font_size=12.0,
    )

    # Bottom Research Questions strip
    add_card(s2, 0.6, 5.05, 12.13, 1.88, "Research Questions", C_TEAL, C_TEAL_SOFT, C_TEAL)
    add_bullets(
        s2, 0.85, 5.58, 11.65, 1.25,
        [
            ("RQ1 (Prediction)", "Does incorporating LLM-derived cognitive skill requirements into KT improve student performance prediction over traditional KT baselines?"),
            ("RQ2 (Explainability)", "Can Cognitive-Aware KT provide more explainable insights into student cognitive strengths and weaknesses than traditional KT?"),
            ("RQ3 (Skill Influence)", "Which cognitive skills exert the greatest influence on student performance prediction within the proposed framework?"),
        ],
        font_size=11.5,
        space_after=4.0,
    )

    # =========================================================================
    # SLIDE 3: 1. INTRODUCTION — AIMS, OBJECTIVES & SCOPE
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "01", "Introduction", "Aims, Research Objectives & Scope", C_INDIGO, 3, total_slides)

    # Aim banner
    aim = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(1.55), Inches(12.13), Inches(0.95))
    aim.adjustments[0] = 0.08
    aim.fill.solid()
    aim.fill.fore_color.rgb = C_INDIGO_SOFT
    aim.line.color.rgb = C_INDIGO
    aim.line.width = Pt(1.2)
    ap = aim.text_frame.paragraphs[0]
    ap.alignment = PP_ALIGN.LEFT
    aim.text_frame.margin_left = Inches(0.25)
    aim.text_frame.margin_right = Inches(0.25)
    aim.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    r_a1 = ap.add_run()
    r_a1.text = "PRIMARY AIM:  "
    r_a1.font.name = "Calibri"
    r_a1.font.size = Pt(13)
    r_a1.font.bold = True
    r_a1.font.color.rgb = C_INDIGO
    r_a2 = ap.add_run()
    r_a2.text = "Develop a Cognitive-Aware Learning Analytics Framework using LLMs and Knowledge Tracing to improve student performance prediction and deliver explainable insights into learner cognitive behavior."
    r_a2.font.name = "Calibri"
    r_a2.font.size = Pt(13)
    r_a2.font.color.rgb = C_DARK_NAVY

    # Three Objective Cards
    ro_data = [
        ("RO1", "Cognitive Skill Extraction", C_BLUE, C_BLUE_SOFT,
         "Identify and represent 6 cognitive skill requirements per question (Attention, Working Memory, Logical Reasoning, Language Processing, Critical Thinking, Metacognition) on a 0–3 scale using multimodal LLMs."),
        ("RO2", "Cognitive-Aware KT Model", C_VIOLET, C_PURPLE_SOFT,
         "Design and train CA-KT integrating question cognitive demand vectors with sequential student interaction histories to model evolving knowledge & cognitive mastery states."),
        ("RO3", "Empirical & Expert Validation", C_EMERALD, C_EMERALD_SOFT,
         "Benchmark prediction accuracy (AUC, Accuracy, RMSE) against DKT, qDKT, and QIKT/QKT baselines, and validate explainable learner profiles alongside an offline LAN exam platform."),
    ]
    for idx, (code, title, col, soft, desc) in enumerate(ro_data):
        x = 0.6 + idx * 4.11
        add_card(s3, x, 2.72, 3.91, 2.5, f"{code}: {title}", col, C_WHITE, col)
        tb = s3.shapes.add_textbox(Inches(x + 0.2), Inches(3.32), Inches(3.5), Inches(1.75))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.line_spacing = 1.2
        r = p.add_run()
        r.text = desc
        r.font.name = "Calibri"
        r.font.size = Pt(12)
        r.font.color.rgb = C_TEXT_DARK

    # Scope & Expected Outcomes
    add_card(s3, 0.6, 5.42, 5.95, 1.5, "Research Scope", C_AMBER)
    add_bullets(
        s3, 0.85, 5.95, 5.45, 0.9,
        [
            ("Focus", "Prediction modeling & explainable cognitive analytics (not automated grading decisions)."),
            ("Ethics", "De-identified data only; LLMs support educators rather than replacing judgment."),
        ],
        font_size=11.0, space_after=3.0,
    )

    add_card(s3, 6.78, 5.42, 5.95, 1.5, "Expected Outcomes", C_TEAL)
    add_bullets(
        s3, 7.03, 5.95, 5.45, 0.9,
        [
            ("Deliverables", "Trained CA-KT model, 6-skill cognitive dataset, explainable profiler, and benchmark report."),
            ("Deployment", "Offline LAN MCQ examination platform ready for Phase 2 school data collection."),
        ],
        font_size=11.0, space_after=3.0,
    )

    # =========================================================================
    # SLIDE 4: 2. PROGRESS — PROJECT MILESTONES & CURRENT STATUS
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "02", "Progress", "Current Progress & Completed Milestones (Aug – Nov 2026)", C_TEAL, 4, total_slides)

    # 4 KPI Cards
    add_kpi_card(s4, 0.6, 1.55, 2.85, 1.2, "7,652 / 7,652", "Questions Annotated", "100% DeepSeek Multimodal (0–3)", C_EMERALD, C_EMERALD_SOFT)
    add_kpi_card(s4, 3.69, 1.55, 2.85, 1.2, "5.55M", "Student Interactions", "18,066 Students (XES3G5M)", C_INDIGO, C_INDIGO_SOFT)
    add_kpi_card(s4, 6.78, 1.55, 2.85, 1.2, "6 / 6 Models", "Full-Dataset Trained", "DKT, qDKT, QIKT & 3x CAKT", C_VIOLET, C_PURPLE_SOFT)
    add_kpi_card(s4, 9.88, 1.55, 2.85, 1.2, "30 / 30 Tests", "All Automated Checks Pass", "22 Python + 8 Node.js Tests", C_TEAL, C_TEAL_SOFT)

    # Progress Table
    rows_prog = [
        ["Milestone / Component", "Timeline", "Status", "Key Achievement"],
        ["1. School Data Collection Attempt", "Aug 4 – Aug 18", "Deferred to Phase 2", "Identified answer-script loss bottleneck; built LAN platform for Phase 2"],
        ["2. XES3G5M + ExRec Data Curation", "Aug 19 – Aug 26", "Completed (100%)", "7,652 Qs (2,214 visual + 2,459 PNGs), 5,549,184 events, zero leakage"],
        ["3. Zero-Cost DeepSeek Extension", "Sep 11 – Nov 11", "Completed (100%)", "Chrome MV3 + Bridge Server annotated all 7,652 Qs at $0 API cost"],
        ["4. Multi-LLM Cross-Validation", "Nov 9 – Present", "In Progress (12/500)", "Gemini Web extension (Port 8767) built; 500-Q Gemini Pro run started"],
        ["5. Baselines & New CA-KT Training", "Nov 11 – Nov 12", "Completed (100%)", "Trained DKT, qDKT, QIKT, Normal/Cluster/New CAKT; New CAKT ranks #1"],
        ["6. Offline LAN Exam App (BrainMapper)", "Nov 1 – Nov 12", "Phases 1–3 Built", "Home, Roster, Quiz Builder (MCQ), QR Monitor & Student Exam Portal live"],
    ]
    tbl_shape = s4.shapes.add_table(len(rows_prog), 4, Inches(0.6), Inches(2.95), Inches(12.13), Inches(3.95))
    tbl = tbl_shape.table
    for i, r in enumerate(rows_prog):
        for j, val in enumerate(r):
            tbl.cell(i, j).text = val
    style_table(tbl, [3.4, 1.85, 2.0, 4.88], header_bg=C_TEAL, font_size=10.5)
    for i in range(1, len(rows_prog)):
        tbl.cell(i, 3).text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT

    # =========================================================================
    # SLIDE 5: 3. RELATED WORK — LITERATURE SUMMARY & RESEARCH GAP
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "03", "Related Work", "Literature Summary & Identified Research Gap", C_BLUE, 5, total_slides)

    # Left: Related Work Table
    rows_lit = [
        ["Model / Family", "Core Mechanism", "Strength", "Limitation Addressed by Brain Mapper"],
        ["BKT (Corbett & Anderson)", "Hidden Markov / Probabilistic", "Interpretable single-skill mastery", "Assumes independent skills; weak on complex items"],
        ["DKT (Piech et al., 2015)", "LSTM Recurrent Neural Net", "Captures long sequential history", "Concept-level only; opaque hidden states"],
        ["DKVMN & SAKT (2017–19)", "Memory Nets / Self-Attention", "Models concept relations & attention", "No question-specific difficulty or cognitive load"],
        ["AKT (Ghosh et al., 2020)", "Monotonic Attention + Rasch", "Rasch embeds reduce overfitting", "Lacks cognitive process profiling"],
        ["qDKT (Sonkar et al., 2020)", "Question-Centric LSTM + Graph", "Distinguishes questions within KCs", "Suffers on sparse/new question IDs"],
        ["QIKT / QKT (Chen / Shen '23)", "Question-Centric + IRT + Quiz", "Strong AUC (72.7–85.4 across sets)", "No explicit cognitive skill demands"],
        ["IRT / NCD (Wang et al., '20)", "Cognitive Diagnosis Models", "Models mastery vs. difficulty", "Relies on costly manual expert Q-matrices"],
    ]
    t5_shape = s5.shapes.add_table(len(rows_lit), 4, Inches(0.6), Inches(1.55), Inches(12.13), Inches(3.95))
    t5 = t5_shape.table
    for i, r in enumerate(rows_lit):
        for j, val in enumerate(r):
            t5.cell(i, j).text = val
    style_table(t5, [2.75, 2.75, 3.05, 3.58], header_bg=C_BLUE, font_size=10.0)
    for i in range(1, len(rows_lit)):
        for j in range(4):
            t5.cell(i, j).text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT

    # Bottom Gap Card
    add_card(s5, 0.6, 5.68, 12.13, 1.28, "Key Research Gap & Brain Mapper Contribution", C_VIOLET, C_PURPLE_SOFT, C_VIOLET)
    add_bullets(
        s5, 0.85, 6.18, 11.65, 0.72,
        [
            ("Gap", "Existing KT models (DKT, qDKT, QIKT) rely on binary responses and curriculum concepts without explicit cognitive demands, while CDMs depend on manual expert Q-matrices."),
            ("Our Contribution", "Automate 6-skill multimodal cognitive estimation via LLMs and fuse it with Rasch-decomposed, cluster-aware KT (CA-KT) + explainable learner profiling."),
        ],
        font_size=11.0, space_after=2.5,
    )

    # =========================================================================
    # SLIDE 6: 4. METHODOLOGY — DATASET & 6-SKILL COGNITIVE EXTRACTION
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "04", "Methodology", "Dataset Curation & 6-Skill Multimodal Cognitive Extraction", C_VIOLET, 6, total_slides)

    # Left: Dataset & Rubric
    add_card(s6, 0.6, 1.55, 5.65, 2.65, "Benchmark Dataset: XES3G5M + ExRec", C_INDIGO)
    add_bullets(
        s6, 0.85, 2.12, 5.15, 2.0,
        [
            ("Origin", "AI4ED / TAL Education Group (NeurIPS) + ExRec English translations (Özyurt et al.)."),
            ("Scale", "18,066 students, 5,549,184 interactions, 7,652 math questions (seq. length 200–913)."),
            ("Multimodal", "2,214 image-dependent problems with 2,459 geometry diagram PNGs."),
            ("Leakage Prevention", "Excluded overlapping test windows; isolated answer keys from LLM prompts."),
        ],
        font_size=11.5, space_after=4.5,
    )

    add_card(s6, 0.6, 4.38, 5.65, 2.52, "Zero-Cost LLM Annotation & Validation", C_TEAL)
    add_bullets(
        s6, 0.85, 4.95, 5.15, 1.85,
        [
            ("Scale", "0 = Not Required, 1 = Low, 2 = Moderate, 3 = High Requirement (+ confidence & rationale)."),
            ("Pipeline", "Chrome MV3 Extension + Python Bridge injects question text & attaches PNGs via File/DataTransfer API into DeepSeek Web."),
            ("Cross-Validation", "Separate Gemini Web extension (Port 8767) tests 500 text-only Qs for inter-LLM agreement without manual human labeling."),
        ],
        font_size=11.2, space_after=4.5,
    )

    # Right: 6 Cognitive Skills Grid
    add_card(s6, 6.48, 1.55, 6.25, 5.35, "Six-Dimensional Cognitive Skill Taxonomy (0–3 Scale)", C_VIOLET)
    skills_info = [
        ("1. Attention", "Selective focus on key elements, visual diagram parsing, filtering extraneous distractors.", C_BLUE_SOFT, C_BLUE),
        ("2. Working Memory", "Retaining and manipulating intermediate steps, variables, and multi-clause constraints.", C_PURPLE_SOFT, C_VIOLET),
        ("3. Logical Reasoning", "Step-by-step deductive/inductive reasoning, geometric proofs, and pattern discovery.", C_INDIGO_SOFT, C_INDIGO),
        ("4. Language Processing", "Decoding domain-specific math phrasing, dense wording, and conditional statements.", C_TEAL_SOFT, C_TEAL),
        ("5. Critical Thinking", "Evaluating alternative pathways, testing edge/boundary cases, and counterexamples.", C_AMBER_SOFT, C_AMBER),
        ("6. Metacognition", "Strategy planning, error self-monitoring, constraint verification, and reflection.", C_ROSE_SOFT, C_ROSE),
    ]
    for idx, (sname, sdesc, sbg, scol) in enumerate(skills_info):
        y = 2.15 + idx * 0.78
        box = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.72), Inches(y), Inches(5.77), Inches(0.68))
        box.adjustments[0] = 0.12
        box.fill.solid()
        box.fill.fore_color.rgb = sbg
        box.line.color.rgb = scol
        box.line.width = Pt(1.0)
        tf = box.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.margin_left = Inches(0.14)
        tf.margin_right = Inches(0.12)
        p = tf.paragraphs[0]
        r1 = p.add_run()
        r1.text = f"{sname}:  "
        r1.font.name = "Calibri"
        r1.font.size = Pt(11.5)
        r1.font.bold = True
        r1.font.color.rgb = scol
        r2 = p.add_run()
        r2.text = sdesc
        r2.font.name = "Calibri"
        r2.font.size = Pt(10.8)
        r2.font.color.rgb = C_TEXT_DARK

    # =========================================================================
    # SLIDE 7: 4. METHODOLOGY — CA-KT MODEL & EVALUATION PROTOCOL
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "04", "Methodology", "Cognitive-Aware Knowledge Tracing (New CA-KT) & Evaluation", C_VIOLET, 7, total_slides)

    # Top Architecture Flow Cards (4 steps)
    flow_steps = [
        ("1. Rasch + Cognitive Item", "Decomposes each item into shared concept + cognitive base plus scalar question variation μ_q to prevent ID memorization.", C_INDIGO),
        ("2. 64 Cognitive Clusters", "K-Means clusters 865 sparse concepts by cognitive demand signatures into 64 dense cognitive concept groups.", C_BLUE),
        ("3. Causal Window-200", "LSTM knowledge acquisition + AKT-style monotonic time-decayed causal attention bounded to recent 200 steps.", C_TEAL),
        ("4. Cognitive-IRT Output", "Predicts correctness via Ability (θ) − Difficulty (β) × Discrimination (α) + interpretable 6-skill mastery ψ_t ∈ (0,1)^6.", C_EMERALD),
    ]
    for idx, (stitle, sbody, scol) in enumerate(flow_steps):
        x = 0.6 + idx * 3.09
        add_card(s7, x, 1.55, 2.89, 2.25, stitle, scol, C_WHITE, scol)
        tb = s7.shapes.add_textbox(Inches(x + 0.16), Inches(2.12), Inches(2.57), Inches(1.55))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.line_spacing = 1.18
        r = p.add_run()
        r.text = sbody
        r.font.name = "Calibri"
        r.font.size = Pt(11.2)
        r.font.color.rgb = C_TEXT_DARK

    # Bottom Two Evaluation Modes + LAN Platform
    add_card(s7, 0.6, 4.02, 6.2, 2.88, "Dual Evaluation Protocol (PyTorch, Seed 42, 8 Epochs)", C_VIOLET)
    add_bullets(
        s7, 0.85, 4.58, 5.7, 2.2,
        [
            ("Standard Benchmark Split", "Official XES3G5M split: 14,453 train/val students (folds 0–4) tested on 3,613 completely unseen students (1.10M interactions)."),
            ("Per-Class Classroom Mode", "Simulates real schools: 2,000-student base pre-training fine-tuned on 5 separate 40-student classes (70% past / 10% val / 20% future quizzes)."),
            ("Metrics", "ROC-AUC (primary), Binary Accuracy, and RMSE across DKT, qDKT, QIKT, and 3 CA-KT variants."),
        ],
        font_size=11.3, space_after=5.0,
    )

    add_card(s7, 7.05, 4.02, 5.68, 2.88, "Offline LAN Exam Platform (Phase 2 Deployment)", C_AMBER)
    add_bullets(
        s7, 7.3, 4.58, 5.2, 2.2,
        [
            ("Purpose", "Enables internet-free Grade 10–11 school quizzes to collect clean MCQ response streams for Phase 2 customization."),
            ("Security & Integrity", "Mandatory unique Student IDs (#ST-xxxx), stripped answer keys in /api/currentQuiz, reload-safe session drafts."),
            ("Zero-Friction Join", "Host runs Express + Electron server; students scan QR code over local Wi-Fi / hotspot."),
        ],
        font_size=11.3, space_after=5.0,
    )

    # =========================================================================
    # SLIDE 8: 5. SYSTEM ARCHITECTURE — END-TO-END & ANNOTATION BRIDGE
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "05", "System Architecture", "End-to-End Pipeline & Zero-Cost LLM Annotation Architecture", C_TEAL, 8, total_slides)

    # Left: Proposal / End-to-End Architecture Summary
    add_card(s8, 0.6, 1.55, 4.2, 5.35, "End-to-End Data Flow", C_INDIGO)
    add_bullets(
        s8, 0.82, 2.15, 3.76, 4.6,
        [
            ("1. Question Input", "7,652 XES3G5M math problems (+ 2,459 PNGs) or educator-authored MCQs."),
            ("2. LLM Cognitive Tagging", "DeepSeek Chrome Extension + Python Bridge generates 0–3 demand vectors with atomic disk sync."),
            ("3. Feature Fusion", "Merges 6D cognitive vectors with student sequential correctness & 64 concept clusters."),
            ("4. New CA-KT Engine", "Predicts per-question success probability & updates 6-skill learner mastery ψ_t."),
            ("5. BrainMapper App", "Delivers offline LAN exams & surfaces pre-quiz forecasts + explainable cognitive radar profiles."),
        ],
        font_size=11.2, space_after=6.5,
    )

    # Right: Diagram fig2
    add_card(s8, 5.0, 1.55, 7.73, 5.35, "Zero-Cost Multimodal Chrome Extension & Python Bridge", C_TEAL)
    fig2 = DIAGRAMS_DIR / "fig2_deepseek_extension_arch.png"
    if fig2.exists():
        s8.shapes.add_picture(str(fig2), Inches(5.18), Inches(2.12), width=Inches(7.38))

    # =========================================================================
    # SLIDE 9: 5. SYSTEM ARCHITECTURE — LAN EXAM & UI DESIGN DIAGRAMS
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "05", "System Architecture", "Offline LAN Network, QR Login & BrainMapper UI Architecture", C_TEAL, 9, total_slides)

    add_card(s9, 0.6, 1.55, 5.95, 5.35, "Offline LAN Examination & QR Login Network", C_BLUE)
    fig3 = DIAGRAMS_DIR / "fig3_lan_network_qr_arch.png"
    if fig3.exists():
        s9.shapes.add_picture(str(fig3), Inches(0.78), Inches(2.15), width=Inches(5.6))

    add_card(s9, 6.78, 1.55, 5.95, 5.35, "Figma UI Architecture & Implemented Interfaces", C_VIOLET)
    if UI_ARCH_IMG.exists():
        s9.shapes.add_picture(str(UI_ARCH_IMG), Inches(6.95), Inches(2.12), width=Inches(5.6))
    else:
        fig4 = DIAGRAMS_DIR / "fig4_frontend_interfaces.png"
        if fig4.exists():
            s9.shapes.add_picture(str(fig4), Inches(6.95), Inches(2.12), width=Inches(5.6))

    cap = s9.shapes.add_textbox(Inches(6.95), Inches(5.75), Inches(5.6), Inches(0.95))
    ctf = cap.text_frame
    ctf.word_wrap = True
    cp = ctf.paragraphs[0]
    cp.line_spacing = 1.15
    cr = cp.add_run()
    cr.text = "Implemented Phases 1–3: Home & Student Roster (#ST-xxxx), Class Dashboard, MCQ Quiz Library & Builder, Live QR Session Monitor (SSE), and Reload-Safe Student Exam Portal (/exam). Phase 4 (Analyze & Live Prediction UI) scheduled next."
    cr.font.name = "Calibri"
    cr.font.size = Pt(10.8)
    cr.font.color.rgb = C_TEXT_DARK

    # =========================================================================
    # SLIDE 10: 6. PRELIMINARY RESULTS — BENCHMARK COMPARISON
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "06", "Preliminary Results", "Full-Dataset Benchmark Results (7,652 Qs / 5.55M Interactions)", C_EMERALD, 10, total_slides)

    # Top Table: Standard & Per-Class Comparison
    rows_res = [
        ["Model", "Standard Test AUC", "Standard Acc", "Standard RMSE", "Per-Class Scratch AUC", "Per-Class Base AUC", "Per-Class Cust. AUC", "Per-Class Cust. RMSE"],
        ["DKT (Baseline)", "0.7743", "81.51%", "0.3659", "0.5156", "0.7087", "0.7085", "0.3950"],
        ["qDKT (Baseline)", "0.8026", "82.27%", "0.3568", "0.4976", "0.7201", "0.7206", "0.3959"],
        ["QIKT (Baseline)", "0.8108", "82.49%", "0.3540", "0.5790", "0.7594", "0.7572", "0.3769"],
        ["Normal CAKT", "0.8117", "82.52%", "0.3537", "0.6115", "0.7540", "0.7518", "0.3804"],
        ["CAKT + Clusters Only", "0.8117", "82.47%", "0.3539", "0.6067", "0.7607", "0.7604", "0.3753"],
        ["New CAKT (Proposed)", "0.8119", "82.51%", "0.3536", "0.6196", "0.7657", "0.7640", "0.3737"],
    ]
    t10_shape = s10.shapes.add_table(len(rows_res), 8, Inches(0.6), Inches(1.52), Inches(12.13), Inches(2.45))
    t10 = t10_shape.table
    for i, r in enumerate(rows_res):
        for j, val in enumerate(r):
            t10.cell(i, j).text = val
    style_table(t10, [2.33, 1.4, 1.25, 1.35, 1.5, 1.4, 1.45, 1.45], header_bg=C_DARK_NAVY, font_size=10.0)
    # Highlight New CAKT row
    for j in range(8):
        c = t10.cell(6, j)
        c.fill.solid()
        c.fill.fore_color.rgb = C_EMERALD_SOFT
        for run in c.text_frame.paragraphs[0].runs:
            run.font.bold = True
            run.font.color.rgb = C_DARK_NAVY

    # Bottom Left: Chart comparing Standard AUC vs Per-Class Customized AUC
    chart_data = CategoryChartData()
    chart_data.categories = ["DKT", "qDKT", "QIKT", "Normal CAKT", "CAKT+Clusters", "New CAKT"]
    chart_data.add_series("Standard Test AUC", (0.7743, 0.8026, 0.8108, 0.8117, 0.8117, 0.8119))
    chart_data.add_series("Per-Class Cust. AUC", (0.7085, 0.7206, 0.7572, 0.7518, 0.7604, 0.7640))
    chart_data.add_series("Per-Class Scratch AUC", (0.5156, 0.4976, 0.5790, 0.6115, 0.6067, 0.6196))

    chart_frame = s10.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(4.12), Inches(7.45), Inches(2.85), chart_data
    )
    chart = chart_frame.chart
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.font.size = Pt(9.5)
    chart.value_axis.minimum_scale = 0.45
    chart.value_axis.maximum_scale = 0.85
    chart.value_axis.major_unit = 0.1
    chart.category_axis.tick_labels.font.size = Pt(9.5)
    chart.value_axis.tick_labels.font.size = Pt(9.0)
    colors_s = [C_INDIGO, C_EMERALD, C_AMBER]
    for idx, ser in enumerate(chart.series):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = colors_s[idx]

    # Bottom Right: Key Takeaways
    add_card(s10, 8.25, 4.12, 4.48, 2.85, "Key Empirical Findings", C_EMERALD)
    add_bullets(
        s10, 8.48, 4.68, 4.05, 2.2,
        [
            ("#1 Across All Splits", "New CAKT achieves highest AUC (0.8119 Standard, 0.7640 Per-Class) and lowest RMSE."),
            ("Small-Class Gains", "On 40-student classes from scratch, New CAKT reaches 0.6196 AUC (+12.2% over qDKT, +4.06% over QIKT)."),
            ("Clusters + Rasch Synergy", "64 cognitive concept clusters + Rasch item decomposition prevent ID overfitting."),
        ],
        font_size=11.0, space_after=5.0,
    )

    # =========================================================================
    # SLIDE 11: 6. PRELIMINARY RESULTS — COGNITIVE CORPUS & VALIDATION
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, "06", "Preliminary Results", "7,652-Question Cognitive Distribution & Cross-Validation", C_EMERALD, 11, total_slides)

    # Left: Chart of Mean Cognitive Skill Demand across 7,652 questions
    cog_chart = CategoryChartData()
    cog_chart.categories = [
        "Logical\nReasoning",
        "Working\nMemory",
        "Attention",
        "Language\nProcessing",
        "Critical\nThinking",
        "Metacognition",
    ]
    cog_chart.add_series("Mean Demand (0–3 Scale)", (2.46, 2.30, 1.87, 1.41, 0.91, 0.16))

    cf2 = s11.shapes.add_chart(
        XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.6), Inches(1.58), Inches(6.55), Inches(3.85), cog_chart
    )
    ch2 = cf2.chart
    ch2.has_legend = False
    ch2.value_axis.minimum_scale = 0.0
    ch2.value_axis.maximum_scale = 3.0
    ch2.category_axis.tick_labels.font.size = Pt(10.0)
    ch2.value_axis.tick_labels.font.size = Pt(9.5)
    ch2.series[0].format.fill.solid()
    ch2.series[0].format.fill.fore_color.rgb = C_VIOLET

    # Bottom-left summary card
    add_card(s11, 0.6, 5.56, 6.55, 1.35, "Corpus Telemetry (7,652 Questions)", C_INDIGO)
    add_bullets(
        s11, 0.85, 6.08, 6.05, 0.78,
        [
            ("Mean Model Confidence", "0.91 across 7,652 questions; 100% schema-validated (0–3 integers)."),
            ("Cognitive Profile", "Math problems demand highest Logical Reasoning (2.46) & Working Memory (2.30)."),
        ],
        font_size=11.0, space_after=3.0,
    )

    # Right: Gemini Cross-Validation + Explainability Status
    add_card(s11, 7.38, 1.58, 5.35, 2.75, "Multi-LLM Cross-Validation (DeepSeek vs. Gemini)", C_TEAL)
    add_bullets(
        s11, 7.62, 2.15, 4.88, 2.08,
        [
            ("Methodology", "500 text-only questions sampled for blind re-annotation via Gemini Web Extension (Port 8767)."),
            ("Gemini Pro Run Active", "12 / 500 paired questions evaluated so far (within-1-point agreement: 83.3%–100.0% across the 6 skills)."),
            ("Next Step", "Complete remaining 488 Gemini Pro annotations to finalize Cohen's weighted κ & Pearson r validation."),
        ],
        font_size=11.3, space_after=5.0,
    )

    add_card(s11, 7.38, 4.52, 5.35, 2.38, "Explainable Learner Profiling (CA-KT)", C_AMBER)
    add_bullets(
        s11, 7.62, 5.08, 4.88, 1.72,
        [
            ("Latent Mastery Vector", "CA-KT outputs interpretable 6-skill mastery ψ_t ∈ (0,1)^6 alongside IRT θ, β, and α."),
            ("Educator Value", "Separates content knowledge gaps from cognitive bottlenecks (e.g., Working Memory overload)."),
        ],
        font_size=11.3, space_after=5.0,
    )

    # =========================================================================
    # SLIDE 12: 7. CHALLENGES & SOLUTIONS
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    add_header(s12, "07", "Challenges & Solutions", "Technical & Operational Challenges Solved", C_ROSE, 12, total_slides)

    rows_ch = [
        ["Area", "Challenge Encountered", "Implemented Solution & Impact"],
        ["School Data Collection", "Answer scripts returned to students were lost; insufficient continuous term-test histories.", "Adopted XES3G5M benchmark (18,066 students) for Phase 1 & built offline LAN Exam platform for Phase 2."],
        ["LLM API Cost & Quotas", "GPT-4o vision (~$35–$55) exceeded budget; free Gemini/Groq APIs hit 500 RPD / TPM caps.", "Built zero-cost Chrome MV3 Extension + Python Bridge for DeepSeek Web Chat ($0 cost, 7,652/7,652 done)."],
        ["Multimodal & DOM Reliability", "2,214 questions needed PNGs; DeepSeek-R1 emitted <think> blocks & caused duplicate/stale reads.", "Automated File/DataTransfer image upload, <think> stripping, anti-stale DOM guards & atomic os.fsync."],
        ["Multi-Member Collaboration", "Windows OneDrive file locks (WinError 32) & git file conflicts during parallel annotation.", "Added retry-safe atomic writes + clean team git workflows across Waruna, Pramudi, Dilshan & Tharindu."],
        ["KT Question Memorization", "Standard models overfit to 7,652 question IDs & 865 sparse concepts on small 40-student classes.", "Introduced Rasch item decomposition + 64 K-Means cognitive concept clusters + 200-step causal window."],
        ["Exam Security Offline", "Need zero-internet exam delivery without leaking answers or breaking on browser refresh.", "Local Express/QR LAN server strips answer keys, enforces #ST-xxxx IDs & restores drafts on reload."],
    ]
    t12_shape = s12.shapes.add_table(len(rows_ch), 3, Inches(0.6), Inches(1.55), Inches(12.13), Inches(5.35))
    t12 = t12_shape.table
    for i, r in enumerate(rows_ch):
        for j, val in enumerate(r):
            t12.cell(i, j).text = val
    style_table(t12, [2.35, 4.45, 5.33], header_bg=C_ROSE, font_size=10.5)
    for i in range(1, len(rows_ch)):
        for j in range(3):
            t12.cell(i, j).text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT

    # =========================================================================
    # SLIDE 13: 8. FUTURE WORK — PLAN & SCHEDULE
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    add_header(s13, "08", "Future Work", "Remaining Plan & 12-Month Schedule Alignment", C_AMBER, 13, total_slides)

    # 4 Phase Cards
    fut_items = [
        ("1. Inference & Explainability", "Months 7–8", C_INDIGO,
         "Implement production Python modules in src/brain_mapper/inference & explainability to compute live per-student cognitive mastery ψ_t and RQ3 skill attribution."),
        ("2. BrainMapper Phase 4 & ML Sync", "Months 8–9", C_VIOLET,
         "Replace 'Work in progress' stubs in Predicted Results & Analyze screens with live New CA-KT pre-quiz forecasts, Quiz Grades, and 6-axis cognitive radar charts."),
        ("3. Cross-Validation & School Data", "Months 9–10", C_TEAL,
         "Finish 500-question Gemini Pro cross-validation and deploy the offline LAN platform in partner Sri Lankan Grade 10–11 classrooms (Phase 2 real cohort)."),
        ("4. Expert Validation & Thesis", "Months 11–12", C_EMERALD,
         "Conduct educational expert evaluation of explainable learner profiles (RQ2), finalize comparative analysis, and complete the final dissertation."),
    ]
    for idx, (ftitle, ftime, fcol, fdesc) in enumerate(fut_items):
        x = 0.6 + idx * 3.09
        add_card(s13, x, 1.55, 2.89, 2.75, ftitle, fcol, C_WHITE, fcol)
        pill = s13.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x + 0.18), Inches(2.08), Inches(1.45), Inches(0.28))
        pill.fill.solid()
        pill.fill.fore_color.rgb = fcol
        pill.line.fill.background()
        pp = pill.text_frame.paragraphs[0]
        pp.alignment = PP_ALIGN.CENTER
        pr = pp.add_run()
        pr.text = ftime
        pr.font.name = "Calibri"
        pr.font.size = Pt(9.5)
        pr.font.bold = True
        pr.font.color.rgb = C_WHITE

        tb = s13.shapes.add_textbox(Inches(x + 0.18), Inches(2.48), Inches(2.53), Inches(1.7))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.line_spacing = 1.18
        r = p.add_run()
        r.text = fdesc
        r.font.name = "Calibri"
        r.font.size = Pt(11.0)
        r.font.color.rgb = C_TEXT_DARK

    # Bottom Gantt-style schedule table
    gantt_rows = [
        ["Phase / Activity (12-Month Proposal Timeplan)", "M1–M3", "M4–M6", "M7–M9", "M10–M12"],
        ["Literature Review, Refined Proposal & XES3G5M Curation", "Completed", "—", "—", "—"],
        ["6-Skill Taxonomy, LLM Cost Study & Zero-Cost DeepSeek Annotation (7,652 Qs)", "—", "Completed", "—", "—"],
        ["CA-KT & Baseline Modeling (DKT, qDKT, QIKT) + BrainMapper Phases 1–3", "—", "Completed", "—", "—"],
        ["Inference/Explainability, Phase 4 UI, Gemini Pro Check & Phase 2 School Trials", "—", "—", "Active / Next", "—"],
        ["Expert Explainability Validation, Final Thesis & Presentation", "—", "—", "—", "Scheduled"],
    ]
    g_shape = s13.shapes.add_table(len(gantt_rows), 5, Inches(0.6), Inches(4.5), Inches(12.13), Inches(2.4))
    gt = g_shape.table
    for i, r in enumerate(gantt_rows):
        for j, val in enumerate(r):
            gt.cell(i, j).text = val
    style_table(gt, [6.53, 1.4, 1.4, 1.4, 1.4], header_bg=C_AMBER, font_size=10.5)
    for i in range(1, len(gantt_rows)):
        gt.cell(i, 0).text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT
        for j in range(1, 5):
            txt = gt.cell(i, j).text
            if txt == "Completed":
                gt.cell(i, j).fill.solid()
                gt.cell(i, j).fill.fore_color.rgb = C_EMERALD_SOFT
            elif txt == "Active / Next":
                gt.cell(i, j).fill.solid()
                gt.cell(i, j).fill.fore_color.rgb = C_AMBER_SOFT
            elif txt == "Scheduled":
                gt.cell(i, j).fill.solid()
                gt.cell(i, j).fill.fore_color.rgb = C_INDIGO_SOFT

    # =========================================================================
    # SLIDE 14: 9. CONCLUSION & Q&A
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    add_header(s14, "09", "Conclusion", "Summary, Contributions & Q&A", C_DARK_NAVY, 14, total_slides)

    add_card(s14, 0.6, 1.55, 6.2, 3.65, "Key Conclusions", C_INDIGO)
    add_bullets(
        s14, 0.85, 2.15, 5.7, 2.95,
        [
            ("Cognitive-Aware Framework Validated", "Successfully fused 6-dimensional LLM cognitive annotations with sequential Knowledge Tracing across 7,652 math items and 5.55M events."),
            ("Superior Predictive Accuracy", "New CA-KT outperforms DKT, qDKT, and QIKT on both Standard unseen-student (0.8119 AUC) and Per-Class small-cohort customization (0.7640 AUC)."),
            ("Zero-Cost Scalable Pipeline", "Browser-bridge automation eliminated API cost barriers while ensuring strict schema & multimodal diagram coverage."),
            ("Deployment-Ready Ecosystem", "Offline LAN Exam Platform (Phases 1–3) establishes a secure pipeline for Phase 2 Grade 10–11 school data collection."),
        ],
        font_size=11.5, space_after=5.5,
    )

    add_card(s14, 7.05, 1.55, 5.68, 3.65, "Limitations & Mitigation", C_TEAL)
    add_bullets(
        s14, 7.3, 2.15, 5.2, 2.95,
        [
            ("LLM Subjectivity", "Mitigated via strict 0–3 rubric, confidence logging, and ongoing 500-question Gemini Pro cross-validation."),
            ("Benchmark vs. Local Curriculum", "XES3G5M models generalized math tracing; Phase 2 LAN school trials will calibrate to Sri Lankan Grade 10–11 cohorts."),
            ("Pending Live UI Wiring", "Inference & explainability endpoints are the immediate next engineering step to activate Predicted Results & Analyze screens."),
        ],
        font_size=11.5, space_after=6.5,
    )

    # Thank you banner
    ty = s14.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(5.42), Inches(12.13), Inches(1.48))
    ty.adjustments[0] = 0.08
    ty.fill.solid()
    ty.fill.fore_color.rgb = C_DARK_NAVY
    ty.line.fill.background()
    tytf = ty.text_frame
    tytf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_ty1 = tytf.paragraphs[0]
    p_ty1.alignment = PP_ALIGN.CENTER
    r_ty1 = p_ty1.add_run()
    r_ty1.text = "Thank You!  Questions & Discussion"
    r_ty1.font.name = "Calibri"
    r_ty1.font.size = Pt(24)
    r_ty1.font.bold = True
    r_ty1.font.color.rgb = C_WHITE

    p_ty2 = tytf.add_paragraph()
    p_ty2.alignment = PP_ALIGN.CENTER
    p_ty2.space_before = Pt(4)
    r_ty2 = p_ty2.add_run()
    r_ty2.text = "Team Brain Mapper  |  L.W.L. Silva, K.A.A. Dilshan, K.A.P.B. Himaranshi, T. Kothlawala  |  SLTC Research University"
    r_ty2.font.name = "Calibri"
    r_ty2.font.size = Pt(12)
    r_ty2.font.color.rgb = RGBColor(0xC7, 0xD2, 0xFE)

    OUT_PPTX.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT_PPTX))
    print(f"Saved presentation: {OUT_PPTX} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    build_presentation()
