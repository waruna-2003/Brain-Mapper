"""
Generate the updated, clean, minimalist Brain Mapper Presentation (.pptx)
featuring the CA-KT Neural Network Architecture in Section 5 (System Architecture)
and mentioning the extension under dataset annotation.
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
OUT_PPTX = PROJECT_ROOT / "docs" / "Brain_Mapper_Simple_Presentation.pptx"
DIAGRAMS_DIR = PROJECT_ROOT / "docs" / "diagrams"
CAKT_ARCH_IMG = DIAGRAMS_DIR / "cakt_neural_network_arch.png"
LAN_ARCH_IMG = DIAGRAMS_DIR / "fig3_lan_network_qr_arch.png"

# Modern Color Palette
C_NAVY = RGBColor(0x0F, 0x17, 0x2A)  # Slate 900
C_INDIGO = RGBColor(0x4F, 0x46, 0xE5)  # Indigo 600
C_BLUE = RGBColor(0x25, 0x63, 0xEB)  # Blue 600
C_VIOLET = RGBColor(0x7C, 0x3A, 0xED)  # Violet 600
C_TEAL = RGBColor(0x0D, 0x94, 0x88)  # Teal 600
C_EMERALD = RGBColor(0x10, 0xB9, 0x81)  # Emerald 500
C_AMBER = RGBColor(0xF5, 0x9E, 0x0B)  # Amber 500
C_ROSE = RGBColor(0xF4, 0x3F, 0x5E)  # Rose 500
C_BG = RGBColor(0xF8, 0xFA, 0xFC)  # Slate 50
C_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
C_CARD_BORDER = RGBColor(0xCB, 0xD5, 0xE1)  # Slate 300
C_TEXT_MAIN = RGBColor(0x1E, 0x29, 0x3B)  # Slate 800
C_TEXT_MUTED = RGBColor(0x64, 0x74, 0x8B)  # Slate 500
C_TEXT_LIGHT = RGBColor(0x94, 0xA3, 0xB8)  # Slate 400


def set_slide_bg(slide, color: RGBColor) -> None:
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_slide_header(
    slide,
    section_number: str,
    section_name: str,
    headline: str,
    accent: RGBColor = C_INDIGO,
    slide_idx: int = 1,
    total_slides: int = 11,
) -> None:
    set_slide_bg(slide, C_BG)

    # Top thin accent
    top = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.08))
    top.fill.solid()
    top.fill.fore_color.rgb = accent
    top.line.fill.background()

    # Section pill
    pill = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.35), Inches(2.6), Inches(0.35))
    pill.adjustments[0] = 0.5
    pill.fill.solid()
    pill.fill.fore_color.rgb = accent
    pill.line.fill.background()
    p = pill.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = f"{section_number} • {section_name.upper()}"
    r.font.name = "Calibri"
    r.font.size = Pt(11)
    r.font.bold = True
    r.font.color.rgb = C_WHITE

    # Headline
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.7), Inches(0.65))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_top = 0
    p2 = tf.paragraphs[0]
    r2 = p2.add_run()
    r2.text = headline
    r2.font.name = "Calibri"
    r2.font.size = Pt(26)
    r2.font.bold = True
    r2.font.color.rgb = C_NAVY

    # Footer
    fb = slide.shapes.add_textbox(Inches(0.8), Inches(7.08), Inches(8.0), Inches(0.3))
    fp = fb.text_frame.paragraphs[0]
    fr = fp.add_run()
    fr.text = "Brain Mapper  |  SLTC Research University"
    fr.font.name = "Calibri"
    fr.font.size = Pt(10)
    fr.font.color.rgb = C_TEXT_LIGHT

    sb = slide.shapes.add_textbox(Inches(11.5), Inches(7.08), Inches(1.0), Inches(0.3))
    sp = sb.text_frame.paragraphs[0]
    sp.alignment = PP_ALIGN.RIGHT
    sr = sp.add_run()
    sr.text = f"{slide_idx} / {total_slides}"
    sr.font.name = "Calibri"
    sr.font.size = Pt(10)
    sr.font.bold = True
    sr.font.color.rgb = C_TEXT_MUTED


def add_simple_card(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    title: str,
    points: list[str],
    accent: RGBColor = C_INDIGO,
    bg_color: RGBColor = C_WHITE,
    icon_text: str = "",
) -> None:
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    card.adjustments[0] = 0.05
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = C_CARD_BORDER
    card.line.width = Pt(1.0)

    # Accent top border
    accent_bar = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(0.1)
    )
    accent_bar.adjustments[0] = 0.5
    accent_bar.fill.solid()
    accent_bar.fill.fore_color.rgb = accent
    accent_bar.line.fill.background()

    # Title box
    tb = slide.shapes.add_textbox(Inches(left + 0.35), Inches(top + 0.22), Inches(width - 0.7), Inches(0.55))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_top = 0
    p = tf.paragraphs[0]
    if icon_text:
        r_icon = p.add_run()
        r_icon.text = f"{icon_text}  "
        r_icon.font.name = "Calibri"
        r_icon.font.size = Pt(18)
    r = p.add_run()
    r.text = title
    r.font.name = "Calibri"
    r.font.size = Pt(18)
    r.font.bold = True
    r.font.color.rgb = C_NAVY

    # Bullets
    tb_b = slide.shapes.add_textbox(Inches(left + 0.35), Inches(top + 0.8), Inches(width - 0.7), Inches(height - 0.95))
    tf_b = tb_b.text_frame
    tf_b.word_wrap = True
    tf_b.margin_left = 0
    tf_b.margin_top = 0

    for idx, pt in enumerate(points):
        p_pt = tf_b.paragraphs[0] if idx == 0 else tf_b.add_paragraph()
        p_pt.space_before = Pt(8)
        p_pt.space_after = Pt(4)
        p_pt.line_spacing = 1.2
        r_pt = p_pt.add_run()
        r_pt.text = f"•  {pt}"
        r_pt.font.name = "Calibri"
        r_pt.font.size = Pt(13.5)
        r_pt.font.color.rgb = C_TEXT_MAIN


def add_big_stat_card(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    number: str,
    label: str,
    desc: str,
    accent: RGBColor,
) -> None:
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    card.adjustments[0] = 0.08
    card.fill.solid()
    card.fill.fore_color.rgb = C_WHITE
    card.line.color.rgb = C_CARD_BORDER
    card.line.width = Pt(1.2)

    tb = slide.shapes.add_textbox(Inches(left + 0.2), Inches(top + 0.22), Inches(width - 0.4), Inches(height - 0.45))
    tf = tb.text_frame
    tf.word_wrap = True

    p1 = tf.paragraphs[0]
    p1.alignment = PP_ALIGN.CENTER
    r1 = p1.add_run()
    r1.text = number
    r1.font.name = "Calibri"
    r1.font.size = Pt(36)
    r1.font.bold = True
    r1.font.color.rgb = accent

    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    p2.space_before = Pt(4)
    r2 = p2.add_run()
    r2.text = label
    r2.font.name = "Calibri"
    r2.font.size = Pt(15)
    r2.font.bold = True
    r2.font.color.rgb = C_NAVY

    p3 = tf.add_paragraph()
    p3.alignment = PP_ALIGN.CENTER
    p3.space_before = Pt(4)
    r3 = p3.add_run()
    r3.text = desc
    r3.font.name = "Calibri"
    r3.font.size = Pt(12)
    r3.font.color.rgb = C_TEXT_MUTED


def build_simple_presentation() -> None:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]
    total = 11

    # =========================================================================
    # SLIDE 1: CLEAN TITLE SLIDE
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s1, C_NAVY)

    # Center Brand Badge
    badge = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4.666), Inches(1.3), Inches(4.0), Inches(0.45))
    badge.adjustments[0] = 0.5
    badge.fill.solid()
    badge.fill.fore_color.rgb = C_INDIGO
    badge.line.fill.background()
    bp = badge.text_frame.paragraphs[0]
    bp.alignment = PP_ALIGN.CENTER
    br = bp.add_run()
    br.text = "BRAIN MAPPER  |  RESEARCH PROGRESS"
    br.font.name = "Calibri"
    br.font.size = Pt(12)
    br.font.bold = True
    br.font.color.rgb = C_WHITE

    # Main Title
    t1 = s1.shapes.add_textbox(Inches(1.5), Inches(2.1), Inches(10.333), Inches(2.0))
    tf1 = t1.text_frame
    tf1.word_wrap = True
    p_title = tf1.paragraphs[0]
    p_title.alignment = PP_ALIGN.CENTER
    r_title = p_title.add_run()
    r_title.text = "A Cognitive-Aware Learning Analytics Framework\nUsing LLMs and Knowledge Tracing"
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(36)
    r_title.font.bold = True
    r_title.font.color.rgb = C_WHITE

    p_sub = tf1.add_paragraph()
    p_sub.alignment = PP_ALIGN.CENTER
    p_sub.space_before = Pt(14)
    r_sub = p_sub.add_run()
    r_sub.text = "Cognitive Skill Demand Extraction  •  CA-KT Performance Prediction  •  Offline LAN Delivery"
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(16)
    r_sub.font.color.rgb = RGBColor(0xC7, 0xD2, 0xFE)

    # Presenters & Affiliation
    card_info = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(2.2), Inches(4.8), Inches(8.933), Inches(1.7))
    card_info.adjustments[0] = 0.08
    card_info.fill.solid()
    card_info.fill.fore_color.rgb = RGBColor(0x1E, 0x29, 0x3B)
    card_info.line.color.rgb = C_INDIGO
    card_info.line.width = Pt(1.0)

    tb_pres = s1.shapes.add_textbox(Inches(2.5), Inches(4.95), Inches(8.333), Inches(1.4))
    ptf = tb_pres.text_frame
    ptf.word_wrap = True

    p_team = ptf.paragraphs[0]
    p_team.alignment = PP_ALIGN.CENTER
    r_team = p_team.add_run()
    r_team.text = "Research Team: L.W.L. Silva (Leader), K.A.A. Dilshan, K.A.P.B. Himaranshi, T. Kothlawala"
    r_team.font.name = "Calibri"
    r_team.font.size = Pt(13)
    r_team.font.bold = True
    r_team.font.color.rgb = C_WHITE

    p_sup = ptf.add_paragraph()
    p_sup.alignment = PP_ALIGN.CENTER
    p_sup.space_before = Pt(4)
    r_sup = p_sup.add_run()
    r_sup.text = "Supervisors: Miss. Risuni Siyara & Dr. Chameera De Silva"
    r_sup.font.name = "Calibri"
    r_sup.font.size = Pt(12)
    r_sup.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)

    p_inst = ptf.add_paragraph()
    p_inst.alignment = PP_ALIGN.CENTER
    p_inst.space_before = Pt(4)
    r_inst = p_inst.add_run()
    r_inst.text = "Department of Data Science  |  SLTC Research University, Sri Lanka"
    r_inst.font.name = "Calibri"
    r_inst.font.size = Pt(12)
    r_inst.font.color.rgb = RGBColor(0x67, 0xE8, 0xF9)

    # =========================================================================
    # SLIDE 2: 1. INTRODUCTION — PROBLEM STATEMENT & OVERVIEW
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_slide_header(s2, "01", "Introduction", "The Problem & The Brain Mapper Solution", C_INDIGO, 2, total)

    add_simple_card(
        s2, 0.8, 1.65, 3.65, 4.9,
        "The Problem",
        [
            "School exams only yield aggregate marks (e.g., 62%). Question-level diagnostic data is lost.",
            "Traditional Knowledge Tracing (DKT, qDKT) is a black box, treating items as opaque IDs.",
            "Teachers cannot diagnose why a student struggles (working memory, logic, or language?).",
            "Manual expert Q-matrix tagging is too expensive and cannot scale to large question banks.",
        ],
        accent=C_ROSE,
        icon_text="⚠️",
    )

    add_simple_card(
        s2, 4.84, 1.65, 3.65, 4.9,
        "Our Solution",
        [
            "Automate cognitive skill scoring (0–3 scale) using Multimodal LLMs.",
            "Evaluate 6 skills: Attention, Working Memory, Logical Reasoning, Language, Critical Thinking, Metacognition.",
            "Design Cognitive-Aware KT (CA-KT) to fuse cognitive vectors with sequential student responses.",
            "Generate actionable cognitive radar profiles for teachers.",
        ],
        accent=C_INDIGO,
        icon_text="💡",
    )

    add_simple_card(
        s2, 8.88, 1.65, 3.65, 4.9,
        "Practical Impact",
        [
            "Accurate Performance Prediction before and during exams.",
            "Explainable Learner Diagnostics: reveals student cognitive strengths and weak spots.",
            "Zero-Internet LAN Exam Platform for seamless deployment in Sri Lankan schools.",
            "Zero ongoing LLM API subscription costs for schools.",
        ],
        accent=C_EMERALD,
        icon_text="🎯",
    )

    # =========================================================================
    # SLIDE 3: 1. INTRODUCTION — AIMS & RESEARCH OBJECTIVES
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_slide_header(s3, "01", "Introduction", "Research Aim & Three Core Objectives", C_INDIGO, 3, total)

    # Big Aim Card
    aim_box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.65), Inches(11.733), Inches(1.3))
    aim_box.adjustments[0] = 0.08
    aim_box.fill.solid()
    aim_box.fill.fore_color.rgb = RGBColor(0xEE, 0xF2, 0xFF)
    aim_box.line.color.rgb = C_INDIGO
    aim_box.line.width = Pt(1.5)

    atf = aim_box.text_frame
    atf.word_wrap = True
    atf.margin_left = Inches(0.3)
    atf.margin_right = Inches(0.3)
    atf.vertical_anchor = MSO_ANCHOR.MIDDLE
    ap1 = atf.paragraphs[0]
    ar1 = ap1.add_run()
    ar1.text = "PRIMARY RESEARCH AIM\n"
    ar1.font.name = "Calibri"
    ar1.font.size = Pt(13)
    ar1.font.bold = True
    ar1.font.color.rgb = C_INDIGO

    ar2 = ap1.add_run()
    ar2.text = "Develop a Cognitive-Aware Learning Analytics Framework using LLMs and Knowledge Tracing to improve student performance prediction and deliver explainable insights into learner cognitive behavior."
    ar2.font.name = "Calibri"
    ar2.font.size = Pt(14)
    ar2.font.color.rgb = C_NAVY

    # 3 Objective Cards
    add_simple_card(
        s3, 0.8, 3.25, 3.65, 3.35,
        "RO1: Cognitive Extraction",
        [
            "Define a 6-skill cognitive rubric (0–3 scale).",
            "Use multimodal LLMs to score math questions & geometry diagrams automatically.",
            "Achieve automated, consistent question annotation.",
        ],
        accent=C_BLUE,
        icon_text="🔍",
    )

    add_simple_card(
        s3, 4.84, 3.25, 3.65, 3.35,
        "RO2: CA-KT Modeling",
        [
            "Design Cognitive-Aware KT (CA-KT).",
            "Combine student interaction sequences with 6D cognitive requirement vectors.",
            "Track evolving cognitive mastery over time.",
        ],
        accent=C_VIOLET,
        icon_text="🧠",
    )

    add_simple_card(
        s3, 8.88, 3.25, 3.65, 3.35,
        "RO3: Empirical Validation",
        [
            "Benchmark against DKT, qDKT, and QIKT.",
            "Evaluate on unseen students & small classes.",
            "Deploy an offline LAN exam system for real school validation.",
        ],
        accent=C_EMERALD,
        icon_text="📊",
    )

    # =========================================================================
    # SLIDE 4: 2. PROGRESS — MILESTONES & CURRENT ACHIEVEMENTS
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_slide_header(s4, "02", "Progress", "What We Have Accomplished So Far", C_TEAL, 4, total)

    # 4 Big Stat Cards
    add_big_stat_card(s4, 0.8, 1.65, 2.7, 2.2, "7,652", "Questions Annotated", "100% Complete via Custom Extension", C_EMERALD)
    add_big_stat_card(s4, 3.81, 1.65, 2.7, 2.2, "5.55M", "Interactions", "18,066 Students (XES3G5M Benchmark)", C_INDIGO)
    add_big_stat_card(s4, 6.82, 1.65, 2.7, 2.2, "6 Models", "Trained & Tested", "DKT, qDKT, QIKT + 3x CA-KT Variants", C_VIOLET)
    add_big_stat_card(s4, 9.83, 1.65, 2.7, 2.2, "30 / 30", "Automated Tests", "22 Python Tests + 8 Node Server Tests", C_TEAL)

    add_simple_card(
        s4, 0.8, 4.25, 5.72, 2.35,
        "Completed Milestones",
        [
            "Curated XES3G5M + ExRec English benchmark (7,652 Qs, 2,459 diagram PNGs).",
            "Developed browser extension to annotate all 7,652 questions on a 0–3 cognitive scale.",
            "Fully trained all baseline & CA-KT models on the full dataset; New CA-KT ranks #1.",
        ],
        accent=C_EMERALD,
    )

    add_simple_card(
        s4, 6.82, 4.25, 5.71, 2.35,
        "Active & Deployment Work",
        [
            "Multi-LLM cross-validation running (500 text questions re-annotated with Gemini Pro).",
            "Built BrainMapper offline LAN exam server (QR code login, student portal).",
            "Ready for Phase 2 real Grade 10–11 school classroom deployment.",
        ],
        accent=C_BLUE,
    )

    # =========================================================================
    # SLIDE 5: 3. RELATED WORK — LITERATURE & RESEARCH GAP
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_slide_header(s5, "03", "Related Work", "Comparison With Existing Approaches", C_BLUE, 5, total)

    add_simple_card(
        s5, 0.8, 1.65, 3.65, 3.75,
        "Traditional KT Models",
        [
            "Models: DKT (2015), SAKT (2019), qDKT (2020), QIKT (2023).",
            "Approach: Track concept IDs and 0/1 correctness using RNNs / Attention.",
            "Limitation: Treats questions as black boxes. Cannot explain student cognitive difficulties.",
        ],
        accent=C_ROSE,
    )

    add_simple_card(
        s5, 4.84, 1.65, 3.65, 3.75,
        "Cognitive Diagnosis Models",
        [
            "Models: Item Response Theory (IRT), Neural Cognitive Diagnosis (NCD).",
            "Approach: Estimate student mastery and question difficulty parameters.",
            "Limitation: Requires expensive manual Q-matrix tagging by human experts. Cannot scale.",
        ],
        accent=C_AMBER,
    )

    add_simple_card(
        s5, 8.88, 1.65, 3.65, 3.75,
        "Brain Mapper (Proposed)",
        [
            "Bridges the Gap: Uses Multimodal LLMs to extract cognitive skills automatically.",
            "Cognitive-Aware KT: Fuses 6 cognitive demands with sequence modeling.",
            "Advantage: High accuracy + interpretable cognitive diagnostics with zero manual tagging.",
        ],
        accent=C_EMERALD,
    )

    gap = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.65), Inches(11.733), Inches(1.15))
    gap.adjustments[0] = 0.08
    gap.fill.solid()
    gap.fill.fore_color.rgb = RGBColor(0xEE, 0xF2, 0xFF)
    gap.line.color.rgb = C_INDIGO
    gap.line.width = Pt(1.0)
    gtf = gap.text_frame
    gtf.word_wrap = True
    gtf.margin_left = Inches(0.3)
    gtf.vertical_anchor = MSO_ANCHOR.MIDDLE
    gp = gtf.paragraphs[0]
    gr1 = gp.add_run()
    gr1.text = "THE CORE RESEARCH GAP:  "
    gr1.font.name = "Calibri"
    gr1.font.size = Pt(12)
    gr1.font.bold = True
    gr1.font.color.rgb = C_INDIGO
    gr2 = gp.add_run()
    gr2.text = "Existing KT models know THAT a student failed a question, but not WHY. Cognitive models know why, but require costly human experts. Brain Mapper uses LLMs to bridge this gap automatically."
    gr2.font.name = "Calibri"
    gr2.font.size = Pt(13)
    gr2.font.color.rgb = C_NAVY

    # =========================================================================
    # SLIDE 6: 4. METHODOLOGY — DATASET & 6 COGNITIVE SKILLS
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_slide_header(s6, "04", "Methodology", "Dataset Curation & 6-Skill Cognitive Extraction", C_VIOLET, 6, total)

    # Left: Dataset & Extension Note
    add_simple_card(
        s6, 0.8, 1.65, 5.72, 4.95,
        "Dataset & Automated Annotation",
        [
            "Benchmark: XES3G5M + ExRec English dataset (18,066 students, 5.55M interactions).",
            "Multimodal: 7,652 questions including 2,214 visual geometry items with 2,459 diagram PNGs.",
            "Automated Extension: Developed custom browser extension to programmatically inject questions and diagram PNGs for LLM cognitive scoring.",
            "Complete Coverage: 100% of questions annotated (0–3 integer scale) with zero manual tagging.",
        ],
        accent=C_BLUE,
        icon_text="📁",
    )

    # Right: The 6 Skills
    add_simple_card(
        s6, 6.82, 1.65, 5.71, 4.95,
        "The 6 Cognitive Skills (0–3 Scale)",
        [
            "Attention (1.87 avg): Focus on key details; visual diagram parsing.",
            "Working Memory (2.30 avg): Holding intermediate steps & formulas.",
            "Logical Reasoning (2.46 avg): Step-by-step deductive math proofs.",
            "Language Processing (1.41 avg): Understanding dense word problems.",
            "Critical Thinking (0.91 avg): Checking alternative options & edge cases.",
            "Metacognition (0.16 avg): Strategy planning & error self-checking.",
        ],
        accent=C_VIOLET,
        icon_text="🧩",
    )

    # =========================================================================
    # SLIDE 7: 5. SYSTEM ARCHITECTURE — CA-KT NEURAL NETWORK ARCHITECTURE
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_slide_header(s7, "05", "System Architecture", "CA-KT Neural Network Architecture", C_INDIGO, 7, total)

    # Full Architecture Diagram Image on Left/Center
    if CAKT_ARCH_IMG.exists():
        s7.shapes.add_picture(str(CAKT_ARCH_IMG), Inches(0.8), Inches(1.6), width=Inches(8.4))

    # Right: Key Architectural Pillars
    add_simple_card(
        s7, 9.4, 1.6, 3.133, 5.0,
        "Core Innovations",
        [
            "Rasch Decomposition:\ne_q = e_base + μ_q · d_var\nstops question-ID memorization.",
            "64 Cognitive Clusters:\ngroups 865 sparse concepts by cognitive requirement signatures.",
            "Causal Attention:\nmonotonic recency decay bounded to 200 interaction steps.",
            "Cognitive IRT Head:\noutputs student ability (θ), difficulty (β), and 6D mastery (ψ_t).",
        ],
        accent=C_INDIGO,
    )

    # =========================================================================
    # SLIDE 8: 5. SYSTEM ARCHITECTURE — OFFLINE LAN EXAM PLATFORM
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_slide_header(s8, "05", "System Architecture", "Offline LAN Examination & Analytics Platform", C_TEAL, 8, total)

    # Left: LAN Diagram
    if LAN_ARCH_IMG.exists():
        s8.shapes.add_picture(str(LAN_ARCH_IMG), Inches(0.8), Inches(1.65), width=Inches(6.2))

    # Right: Simple Feature Cards
    add_simple_card(
        s8, 7.25, 1.65, 5.28, 4.95,
        "Built for Sri Lankan Classrooms",
        [
            "Zero Internet Needed: Runs over local Wi-Fi router or phone hotspot.",
            "QR Code Login: Students scan QR code with phone camera to join exam.",
            "Unique Student IDs: Uses #ST-xxxx IDs; binds to class roster automatically.",
            "Exam Integrity: Strips answer keys from student network responses.",
            "Crash & Reload Proof: Saves auto-drafts every 3 seconds to prevent lost work.",
        ],
        accent=C_BLUE,
    )

    # =========================================================================
    # SLIDE 9: 6. PRELIMINARY RESULTS — ACCURACY & CLASSROOM GAINS
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_slide_header(s9, "06", "Preliminary Results", "New CA-KT Achieves State-of-the-Art Accuracy", C_EMERALD, 9, total)

    # Chart on Left
    chart_data = CategoryChartData()
    chart_data.categories = ["DKT", "qDKT", "QIKT", "New CA-KT"]
    chart_data.add_series("Standard Test AUC (Unseen Students)", (0.7743, 0.8026, 0.8108, 0.8119))
    chart_data.add_series("Classroom Fine-Tuned AUC", (0.7085, 0.7206, 0.7572, 0.7640))
    chart_data.add_series("Classroom From-Scratch AUC (40 Students)", (0.5156, 0.4976, 0.5790, 0.6196))

    cf = s9.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.8), Inches(1.65), Inches(6.8), Inches(4.9), chart_data
    )
    chart = cf.chart
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.font.size = Pt(10)
    chart.value_axis.minimum_scale = 0.45
    chart.value_axis.maximum_scale = 0.85
    chart.category_axis.tick_labels.font.size = Pt(11)

    colors_ = [C_INDIGO, C_EMERALD, C_AMBER]
    for idx, ser in enumerate(chart.series):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = colors_[idx]

    # Right: 3 Big Takeaway Cards
    add_simple_card(
        s9, 7.85, 1.65, 4.68, 4.9,
        "Key Findings",
        [
            "#1 in Accuracy: New CA-KT achieves 0.8119 AUC on unseen students, beating DKT, qDKT, and QIKT.",
            "Solves Small-Class Problem: On small 40-student classes from scratch, CA-KT gets 0.6196 (+12.2% over qDKT).",
            "Highest Fine-Tuned Score: Fine-tuning base weights on a class's history yields 0.7640 AUC (80.88% accuracy).",
            "Rasch + Clusters: Proves that cognitive clustering prevents models from overfitting on small data.",
        ],
        accent=C_EMERALD,
    )

    # =========================================================================
    # SLIDE 10: 7. CHALLENGES & SOLUTIONS
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_slide_header(s10, "07", "Challenges & Solutions", "Major Obstacles & How We Solved Them", C_ROSE, 10, total)

    add_simple_card(
        s10, 0.8, 1.65, 3.65, 4.9,
        "1. School Data Loss",
        [
            "Challenge: Schools hand answer scripts back to students, who lose them. Insufficient past data.",
            "Solution: Adopted the 18,066-student XES3G5M benchmark for Phase 1.",
            "Long-term Fix: Built the offline LAN platform to collect Phase 2 school data digitally.",
        ],
        accent=C_BLUE,
        icon_text="📁",
    )

    add_simple_card(
        s10, 4.84, 1.65, 3.65, 4.9,
        "2. High API Costs",
        [
            "Challenge: Commercial LLM APIs (GPT-4o vision) cost $35–$55, and free tiers hit strict daily limits.",
            "Solution: Built our own Chrome Extension for DeepSeek Web chat.",
            "Result: 100% of all 7,652 questions annotated at $0 total API cost.",
        ],
        accent=C_AMBER,
        icon_text="💰",
    )

    add_simple_card(
        s10, 8.88, 1.65, 3.65, 4.9,
        "3. Small Class Overfitting",
        [
            "Challenge: Training KT on 40 students causes models to memorize question IDs and fail.",
            "Solution: Rasch item decomposition + 64 K-Means cognitive concept clusters.",
            "Result: Reached 0.6196 AUC from scratch (+12.2% over qDKT).",
        ],
        accent=C_EMERALD,
        icon_text="⚡",
    )

    # =========================================================================
    # SLIDE 11: 8. FUTURE WORK & 9. CONCLUSION
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_slide_header(s11, "08 & 09", "Future Work & Conclusion", "Next Steps & Final Summary", C_NAVY, 11, total)

    add_simple_card(
        s11, 0.8, 1.65, 5.72, 3.75,
        "Future Work (Months 7–12)",
        [
            "Connect Model to UI: Wire New CA-KT checkpoints into the BrainMapper web app for real-time predictions.",
            "Finish Cross-Validation: Complete 500-question Gemini Pro validation on port 8767.",
            "Classroom Pilot: Conduct Phase 2 offline exams in partner Sri Lankan Grade 10–11 classrooms.",
            "Expert Evaluation: Validate cognitive radar profiles with mathematics lecturers and teachers.",
        ],
        accent=C_INDIGO,
        icon_text="🚀",
    )

    add_simple_card(
        s11, 6.82, 1.65, 5.71, 3.75,
        "Conclusion",
        [
            "Concept Proven: Incorporating cognitive skill demands significantly improves Knowledge Tracing accuracy.",
            "New CA-KT Ranks #1: Outperforms DKT, qDKT, and QIKT across both standard and per-class splits.",
            "Zero-Cost Pipeline: Demonstrated that large-scale educational annotation can be achieved with $0 API budget.",
            "Classroom-Ready: Offline LAN platform ensures practical deployment in real schools.",
        ],
        accent=C_EMERALD,
        icon_text="🏆",
    )

    ty_card = s11.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.65), Inches(11.733), Inches(1.2))
    ty_card.adjustments[0] = 0.1
    ty_card.fill.solid()
    ty_card.fill.fore_color.rgb = C_NAVY
    ty_card.line.fill.background()

    ttf = ty_card.text_frame
    ttf.word_wrap = True
    ttf.vertical_anchor = MSO_ANCHOR.MIDDLE

    tp1 = ttf.paragraphs[0]
    tp1.alignment = PP_ALIGN.CENTER
    tr1 = tp1.add_run()
    tr1.text = "Thank You! Questions & Discussion"
    tr1.font.name = "Calibri"
    tr1.font.size = Pt(22)
    tr1.font.bold = True
    tr1.font.color.rgb = C_WHITE

    tp2 = ttf.add_paragraph()
    tp2.alignment = PP_ALIGN.CENTER
    tp2.space_before = Pt(3)
    tr2 = tp2.add_run()
    tr2.text = "Team Brain Mapper  |  SLTC Research University"
    tr2.font.name = "Calibri"
    tr2.font.size = Pt(12)
    tr2.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)

    OUT_PPTX.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT_PPTX))
    print(f"Saved updated simple presentation: {OUT_PPTX} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    build_simple_presentation()
