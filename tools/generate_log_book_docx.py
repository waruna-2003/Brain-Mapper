"""
Generate the conversational, timeline-organized Brain Mapper Project Log Book (.docx)
matching the handwritten structure and embedding all 4 architectural/UI diagrams.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls


def set_cell_background(cell, hex_color: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=140, right=140) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'  <w:top w:w="{top}" w:type="dxa"/>'
        f'  <w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'  <w:left w:w="{left}" w:type="dxa"/>'
        f'  <w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def format_table(table, col_widths, header_bg="1A365D", header_fg="FFFFFF", alt_bg="F8FAFC") -> None:
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(table.rows):
        is_header = (i == 0)
        trPr = row._tr.get_or_add_trPr()
        trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
        if is_header:
            trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))

        for j, cell in enumerate(row.cells):
            cell.width = Inches(col_widths[j])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell, top=110, bottom=110, left=130, right=130)

            if is_header:
                set_cell_background(cell, header_bg)
                for p in cell.paragraphs:
                    for r in p.runs:
                        r.font.bold = True
                        r.font.color.rgb = RGBColor.from_string(header_fg)
                        r.font.size = Pt(9.5)
            else:
                set_cell_background(cell, "FFFFFF" if i % 2 == 1 else alt_bg)
                for p in cell.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(9.2)
                        r.font.color.rgb = RGBColor(45, 55, 72)

            tcPr = cell._tc.get_or_add_tcPr()
            borders = parse_xml(
                f'<w:tcBorders {nsdecls("w")}>'
                f'  <w:top w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
                f'  <w:left w:val="none"/>'
                f'  <w:bottom w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
                f'  <w:right w:val="none"/>'
                f'</w:tcBorders>'
            )
            tcPr.append(borders)


def add_diagram(doc: Document, img_path: Path, caption: str, width_inches: float = 6.4) -> None:
    """Embed a diagram centered with a clean caption."""
    if not img_path.exists():
        raise FileNotFoundError(f"Required diagram not found: {img_path}")

    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(6)
    p_img.paragraph_format.space_after = Pt(2)
    p_img.paragraph_format.keep_with_next = True
    run_img = p_img.add_run()
    run_img.add_picture(str(img_path), width=Inches(width_inches))

    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(0)
    p_cap.paragraph_format.space_after = Pt(10)
    r_cap = p_cap.add_run(caption)
    r_cap.font.italic = True
    r_cap.font.size = Pt(9.0)
    r_cap.font.color.rgb = RGBColor(100, 116, 139)


def build_log_book() -> None:
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.85)
        section.bottom_margin = Inches(0.85)
        section.left_margin = Inches(0.95)
        section.right_margin = Inches(0.95)

        hp = section.header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hr = hp.add_run("Brain Mapper — Project Log Book")
        hr.font.size = Pt(8.5)
        hr.font.color.rgb = RGBColor(148, 163, 184)

        fp = section.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        fr = fp.add_run("Project Development Log | August 4 – November 10, 2026")
        fr.font.size = Pt(8.5)
        fr.font.color.rgb = RGBColor(148, 163, 184)

    style_normal = doc.styles["Normal"]
    style_normal.font.name = "Calibri"
    style_normal.font.size = Pt(10.5)
    style_normal.font.color.rgb = RGBColor(45, 55, 72)
    style_normal.paragraph_format.line_spacing = 1.2
    style_normal.paragraph_format.space_after = Pt(5)

    def add_section_header(date_tag: str, title: str) -> None:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True

        r_date = p.add_run(f"[{date_tag}]  ")
        r_date.font.bold = True
        r_date.font.size = Pt(11.5)
        r_date.font.color.rgb = RGBColor(13, 148, 136)  # Teal badge

        r_title = p.add_run(title)
        r_title.font.bold = True
        r_title.font.size = Pt(13.5)
        r_title.font.color.rgb = RGBColor(26, 54, 93)  # Navy

    def add_bullet(text: str, bold_prefix: str = "") -> None:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.18
        if bold_prefix:
            rb = p.add_run(bold_prefix)
            rb.font.bold = True
            rb.font.color.rgb = RGBColor(26, 54, 93)
        rt = p.add_run(text)
        rt.font.color.rgb = RGBColor(45, 55, 72)

    # -------------------------------------------------------------
    # Title Header
    # -------------------------------------------------------------
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(2)
    rt = p_title.add_run("Brain Mapper: Project Log Book")
    rt.font.size = Pt(22)
    rt.font.bold = True
    rt.font.color.rgb = RGBColor(26, 54, 93)

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(10)
    rs = p_sub.add_run("Development Journey, Dataset Collection, AI Annotation & Offline LAN Exam Design")
    rs.font.size = Pt(11.5)
    rs.font.color.rgb = RGBColor(43, 108, 176)

    # Project Info Card Table
    info_tbl = doc.add_table(rows=4, cols=2)
    info_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    info_rows = [
        ("Project Name", "Brain Mapper — Cognitive-Aware Knowledge Tracing & Student Performance Prediction"),
        ("Team Members", "Waruna Silva (Leader), Pramudi Biyonika, Dilshan Kodithuwakku, Tharindu"),
        ("Log Period", "August 4, 2026 – November 10, 2026"),
        ("Repository", "https://github.com/waruna-2003/Brain-Mapper.git (Main Branch)"),
    ]
    for idx, (k, v) in enumerate(info_rows):
        c0, c1 = info_tbl.rows[idx].cells[0], info_tbl.rows[idx].cells[1]
        c0.width, c1.width = Inches(1.8), Inches(4.7)
        c0.paragraphs[0].paragraph_format.space_after = Pt(0)
        c1.paragraphs[0].paragraph_format.space_after = Pt(0)
        r0 = c0.paragraphs[0].add_run(k)
        r0.font.bold = True
        r0.font.size = Pt(9.5)
        r0.font.color.rgb = RGBColor(26, 54, 93)
        r1 = c1.paragraphs[0].add_run(v)
        r1.font.size = Pt(9.5)
        set_cell_background(c0, "EDF2F7")
        set_cell_background(c1, "F8FAFC")
        set_cell_margins(c0, 75, 75, 110, 110)
        set_cell_margins(c1, 75, 75, 110, 110)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # -------------------------------------------------------------
    # Realistic Chronological Timeline Summary Table
    # -------------------------------------------------------------
    p_tl_hdr = doc.add_paragraph()
    p_tl_hdr.paragraph_format.space_before = Pt(4)
    p_tl_hdr.paragraph_format.space_after = Pt(4)
    p_tl_hdr.paragraph_format.keep_with_next = True
    rtl = p_tl_hdr.add_run("Project Timeline Overview (Aug 4 – Nov 10, 2026)")
    rtl.font.bold = True
    rtl.font.size = Pt(12.5)
    rtl.font.color.rgb = RGBColor(26, 54, 93)

    timeline_rows = [
        ("Aug 4 – Aug 18", "School Data Collection Attempt", "Contacted schools for Grade 10/11 & 12/13 papers and marks; hit answer script & timeline bottlenecks."),
        ("Aug 19 – Aug 26", "Found XES3G5M Benchmark", "Adopted XES3G5M (AI4ED / NeurIPS) + ExRec English dataset (7,652 Qs, 18,066 students, 5.5M events)."),
        ("Aug 29 – Sep 10", "LLM API Trials & Cost Analysis", "Evaluated Gemini, DeepSeek, ChatGPT, and Groq APIs; hit daily quotas & high vision token costs."),
        ("Sep 11 – Oct 19", "Zero-Cost DeepSeek Extension", "Leader Waruna proposed browser automation; built Chrome Extension + Python Bridge Server ($0 cost)."),
        ("Oct 20 – Nov 10", "Team Annotation & Bug Fixes", "Fixed Windows locks, <think> parsing, and tab reload issues; team annotated 5,076 / 7,652 Qs (66.3%)."),
        ("Oct 28 – Nov 10", "Multi-LLM Cross-Validation", "Built Gemini Web extension (500 text Qs) to cross-check without human grading; upgraded to Gemini Pro."),
        ("Nov 1 – Nov 10", "LAN Exam & Figma Frontend", "Set up Router/Hotspot LAN server + QR login; designed Figma UI & built user connect and quiz creator."),
    ]
    t_tl = doc.add_table(rows=len(timeline_rows) + 1, cols=3)
    t_tl.rows[0].cells[0].paragraphs[0].text = "Timeline"
    t_tl.rows[0].cells[1].paragraphs[0].text = "Phase / Milestone"
    t_tl.rows[0].cells[2].paragraphs[0].text = "What We Did"
    for i, (dt, ph, desc) in enumerate(timeline_rows):
        row = t_tl.rows[i + 1]
        row.cells[0].paragraphs[0].text = dt
        row.cells[1].paragraphs[0].text = ph
        row.cells[2].paragraphs[0].text = desc
    format_table(t_tl, [1.25, 1.85, 3.4], header_bg="1A365D")

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # -------------------------------------------------------------
    # Entry 1: School Data Collection -> XES3G5M Dataset (Handwritten Page 1)
    # -------------------------------------------------------------
    add_section_header("Aug 4 – Aug 26, 2026", "1. Starting Data Collection & Finding the XES3G5M Dataset")

    doc.add_paragraph(
        "First, we started our data collection process. Just as we planned in our research proposal, we decided to collect real "
        "question papers and term test marks from Grade 10 and 11 students (and we also checked Grade 12 and 13 classes). We contacted "
        "many schools, teachers, and principals to ask for past test data. Some schools agreed to share their students' data with us, "
        "while others declined."
    )
    doc.add_paragraph(
        "Even when we visited the schools that agreed, we ran into a practical roadblock when collecting from students: usually schools "
        "hand evaluated answer scripts straight back to the students after marking is done, and most students had already lost or "
        "misplaced their papers. Within our limited time period, we could not gather enough continuous question-and-answer histories "
        "to train a Knowledge Tracing model properly. Our plan is to complete local school data collection in Phase 2 using our own exam "
        "platform, and in the meantime, we needed a strong benchmark dataset so we could train our model, beat the accuracy of existing "
        "models (like DKT, qDKT, and QKT), and prove that our approach predicts student performance better. That led us to find the XES3G5M dataset."
    )

    p_ds_hdr = doc.add_paragraph()
    p_ds_hdr.paragraph_format.space_before = Pt(4)
    p_ds_hdr.paragraph_format.space_after = Pt(2)
    p_ds_hdr.paragraph_format.keep_with_next = True
    r_dsh = p_ds_hdr.add_run("About the XES3G5M Dataset:")
    r_dsh.font.bold = True
    r_dsh.font.color.rgb = RGBColor(43, 108, 176)

    add_bullet("The dataset was developed and published by the AI4ED research initiative (TAL Education Group) in the NeurIPS track.")
    add_bullet("XES3G5M is widely recognized as the premier benchmark for multimodal mathematical knowledge tracing.")
    add_bullet("Our team incorporated the ExRec benchmark (Özyurt et al.), which gave us validated English translations of the question statements, answer choices, and curriculum knowledge components.")
    add_bullet("It contains 18,066 unique secondary school students, 5,549,184 sequential interaction events, and 7,652 unique mathematical problems (including 2,214 visual geometry problems accompanied by 2,459 real diagram PNGs).")

    # -------------------------------------------------------------
    # Entry 2: Second Effort - Commercial LLM API Cost Analysis (Handwritten Page 1 Bottom)
    # -------------------------------------------------------------
    add_section_header("Aug 29 – Sep 10, 2026", "2. Second Effort: Checking Commercial LLM APIs & Costs")

    doc.add_paragraph(
        "Our second major effort was to annotate all 7,652 questions with cognitive skill scores using Large Language Models (LLMs). "
        "At first, we decided to use commercially available LLM APIs to annotate the dataset automatically. Before running the full corpus, "
        "we calculated the estimated API cost and practical limits for annotating each question one by one across four popular LLM APIs "
        "(Gemini, DeepSeek, ChatGPT, and Groq), as shown below:"
    )

    add_diagram(
        doc,
        Path("docs/diagrams/fig1_llm_api_costs.png"),
        "Figure 1: Cost and rate-limit comparison across Gemini, DeepSeek, ChatGPT, and Groq APIs for 7,652 questions.",
        width_inches=6.5,
    )

    doc.add_paragraph(
        "As the numbers showed, paying per question on ChatGPT (~$35–$55 USD for multimodal GPT-4o vision) or setting up paid billing "
        "projects on Gemini/DeepSeek was expensive for our student budget. Meanwhile, free API tiers were heavily restricted: Gemini's free "
        "tier capped out at 500 requests per day (stopping us after 980 questions), Groq hit strict token-per-minute limits, and DeepSeek's "
        "text API couldn't easily process our 2,459 diagram PNGs directly."
    )

    # -------------------------------------------------------------
    # Entry 3: Waruna's Zero-Cost Idea - Browser Extension Architecture (Handwritten Page 2 Top)
    # -------------------------------------------------------------
    add_section_header("Sep 11 – Oct 26, 2026", "3. Zero-Cost DeepSeek Annotation via Browser Extension & Local Server")

    doc.add_paragraph(
        "To solve this cost issue, our team leader Waruna brought up an idea to annotate the entire dataset without any cost. "
        "Here was the idea: we can use DeepSeek's frontier model in normal web chat conversations for free instead of calling a paid API. "
        "We created a Chrome browser extension to communicate between the browser and a local Python server running on our PC. The extension "
        "automates inputting each question (along with attaching any geometry diagram images) and collects the generated JSON answer, while "
        "the local server is responsible for validating the scores and saving all collected data safely to disk. Here is the architecture of how it works:"
    )

    add_diagram(
        doc,
        Path("docs/diagrams/fig2_deepseek_extension_arch.png"),
        "Figure 2: Zero-Cost Browser Extension and Local Python Bridge Server Architecture.",
        width_inches=6.5,
    )

    doc.add_paragraph(
        "While running this system across our computers (Waruna, Pramudi, and Dilshan), we fixed several practical bugs—such as stripping "
        "DeepSeek-R1's <think> blocks cleanly, adding anti-stale checks so it never grabs an old message by mistake, prompting the user to press F5 "
        "if a browser tab was opened early, and fixing Windows OneDrive file locking issues (WinError 32). By November 10, 2026, our team "
        "successfully completed 5,076 out of 7,652 questions (66.34%), with 2,576 questions remaining."
    )

    # -------------------------------------------------------------
    # Entry 4: Validating Dataset Annotation Across Multiple LLMs (Handwritten Page 2 Middle)
    # -------------------------------------------------------------
    add_section_header("Oct 28 – Nov 10, 2026", "4. Validating Annotations Across Multiple LLMs (Cross-Validation)")

    doc.add_paragraph(
        "Because we didn't have human manual verification for all 7,652 questions, we decided to validate our dataset annotation process by "
        "having different LLMs annotate a sample of questions and checking how similar their answers were. At first we created a test extension "
        "for ChatGPT, though its web editor made consistent automation difficult. So we switched to Google Gemini and built a separate Chrome "
        "extension and local bridge server (port 8767) specifically focused on 500 text-based questions."
    )
    doc.add_paragraph(
        "An initial validation run using a free Gemini account (202 paired questions) showed strong agreement with DeepSeek—achieving 95.2% "
        "within-1-point agreement across all 6 cognitive skills (with almost identical averages on Working Memory: 2.13 vs 2.10, and Logical "
        "Reasoning: 2.14 vs 2.08). On November 10, 2026, we cleared the free-tier test run and reset the Gemini server to run a clean, full "
        "500-question cross-validation pass using a Gemini Pro account."
    )

    # -------------------------------------------------------------
    # Entry 5: Application Development - LAN Network & QR Connection (Handwritten Page 2 Bottom)
    # -------------------------------------------------------------
    add_section_header("Nov 1 – Nov 7, 2026", "5. Application Development: Offline LAN Network & QR Code Login")

    doc.add_paragraph(
        "Next, we started developing our examination application so that in Phase 2 we can easily collect real student data from Grade 10 and 11 "
        "classes inside schools without needing an internet connection. First, we designed our LAN network setup, which is created using a simple "
        "wireless router or a mobile hotspot. Inside the instructor's PC, we run a local virtual server (QuizServer). Because all student phones, "
        "tablets, or laptops are connected to the same local Wi-Fi network, they can communicate directly with the instructor's PC via its IP address."
    )
    doc.add_paragraph(
        "To make joining super easy for students—without needing to manually type a confusing IP link—we wrapped the server URL inside a QR code. "
        "Now students just scan the QR code with their phone camera and log straight into the instructor's virtual server. Here is how our main "
        "examination network works:"
    )

    add_diagram(
        doc,
        Path("docs/diagrams/fig3_lan_network_qr_arch.png"),
        "Figure 3: Offline LAN Examination Network & QR Code Student Login Architecture.",
        width_inches=6.5,
    )

    # -------------------------------------------------------------
    # Entry 6: Frontend UI Interfaces Designed in Figma (Handwritten Page 3)
    # -------------------------------------------------------------
    add_section_header("Nov 4 – Nov 10, 2026", "6. Creating Main Frontend User Interfaces (Figma -> Implementation)")

    doc.add_paragraph(
        "Then we designed the user interfaces of the application in Figma and started building the frontend screens. Specifically, we implemented "
        "the user connecting part (displaying the instructor's LAN IP, scannable QR code, and live participant count alongside the student join screen) "
        "and the quiz creating part (where the instructor enters quiz titles, adds questions and options, attaches images, and sets timers). "
        "The full LAN exam platform is still under active development as we work toward integrating our Knowledge Tracing model and analytics."
    )

    add_diagram(
        doc,
        Path("docs/diagrams/fig4_frontend_interfaces.png"),
        "Figure 4: Main Frontend Interfaces (Figma Design implemented for QR Connection, Quiz Creation, and Student View).",
        width_inches=6.5,
    )

    # -------------------------------------------------------------
    # Current Status Snapshot Table (Nov 10, 2026)
    # -------------------------------------------------------------
    add_section_header("Nov 10, 2026", "7. Current Project Status Snapshot")

    status_rows = [
        ("DeepSeek Annotation Corpus", "5,076 / 7,652 completed (66.34%); 2,576 remaining (resuming at Q#3360)."),
        ("Gemini Pro Cross-Validation", "Extension built on Port 8767 for 500 text-only Qs; reset cleanly to 0/500 for Gemini Pro run."),
        ("LAN Examination Application", "Figma UI designed; User Connecting (QR + LAN IP) & Quiz Creation parts built; CA-KT analytics pending."),
        ("Automated Test Suites", "29 / 29 Python tests passing + 4 / 4 Node.js LAN Exam server tests passing."),
    ]
    t_st = doc.add_table(rows=len(status_rows) + 1, cols=2)
    t_st.rows[0].cells[0].paragraphs[0].text = "Component"
    t_st.rows[0].cells[1].paragraphs[0].text = "Current Status"
    for i, (comp, st) in enumerate(status_rows):
        row = t_st.rows[i + 1]
        row.cells[0].paragraphs[0].text = comp
        row.cells[1].paragraphs[0].text = st
    format_table(t_st, [2.2, 4.3], header_bg="0D9488")

    out_docs = Path("docs/Brain_Mapper_Project_Log_Book.docx")
    out_docs.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_docs))
    print(f"Successfully generated Word log book: {out_docs.resolve()}")

    artifact_dir = Path(r"C:\Users\USER\.gemini\antigravity\brain\e9ede638-c757-4199-abca-a546592f6da5")
    if artifact_dir.exists():
        out_art = artifact_dir / "Brain_Mapper_Project_Log_Book.docx"
        shutil.copyfile(out_docs, out_art)
        print(f"Copied Word log book to artifacts: {out_art}")


if __name__ == "__main__":
    build_log_book()
