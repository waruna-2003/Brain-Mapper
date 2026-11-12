"""
Generate a professional PDF of simple, conversational speaker notes
for the 11 slides of the Brain Mapper presentation using ReportLab.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = PROJECT_ROOT / "docs" / "Brain_Mapper_Speaker_Notes.pdf"
PDF_PATH.parent.mkdir(parents=True, exist_ok=True)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and display total page count."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))

        # Header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 750, "Brain Mapper — Simple Presentation Speaker Notes")
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#94A3B8"))
            self.drawRightString(558, 750, "SLTC Research University")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.75)
            self.line(54, 742, 558, 742)

        # Footer (all pages)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#94A3B8"))
        self.drawString(54, 36, "Research Team: L.W.L. Silva, K.A.A. Dilshan, K.A.P.B. Himaranshi, T. Kothlawala")
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#4F46E5"))
        self.drawRightString(558, 36, f"Page {self._pageNumber} of {total_pages}")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.75)
        self.line(54, 48, 558, 48)

        self.restoreState()


def build_pdf() -> None:
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DocSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12,
    )
    slide_hdr_style = ParagraphStyle(
        "SlideHeader",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1E1B4B"),
    )
    slide_meta_style = ParagraphStyle(
        "SlideMeta",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#4F46E5"),
    )
    cue_style = ParagraphStyle(
        "VisualCue",
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0D9488"),
        spaceAfter=6,
    )
    script_style = ParagraphStyle(
        "SpokenScript",
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=6,
    )
    tip_style = ParagraphStyle(
        "DefenseTip",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#B45309"),
    )

    story = []

    # Title Banner
    story.append(Paragraph("Brain Mapper: Presentation Speaker Notes", title_style))
    story.append(
        Paragraph(
            "<b>Companion Speaking Script for the 11-Slide Progress Presentation</b><br/>"
            "Spoken script written in simple, clear English with estimated timings and defense tips.",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#4F46E5"), spaceAfter=14))

    # Notes content for each slide
    slides_data = [
        {
            "num": "Slide 1",
            "section": "Title Slide",
            "title": "A Cognitive-Aware Learning Analytics Framework Using LLMs and Knowledge Tracing",
            "time": "⏱️ Estimated Time: 45 seconds",
            "cue": "👀 <b>What is on screen:</b> Clean navy title slide with project title, team members, supervisors, and SLTC Research University logo.",
            "script": (
                "\"Good morning respected evaluators, lecturers, and colleagues.<br/><br/>"
                "Today, our team is presenting our research project titled <b>'A Cognitive-Aware Learning Analytics Framework Using Large Language Models and Knowledge Tracing'</b>.<br/><br/>"
                "Our team members are Waruna Silva as leader, Dilshan, Pramudi, and Tharindu, under the guidance of Miss Risuni Siyara and Dr. Chameera De Silva.<br/><br/>"
                "In simple terms, our project combines Artificial Intelligence with classroom test data. We use modern AI models to understand <i>how</i> students think when solving math problems, predict their future test results, and give teachers clear advice on how to help each student.\""
            ),
            "tip": "💡 <b>Quick Tip:</b> Speak clearly and with good energy. Introduce all team members and supervisors with respect.",
        },
        {
            "num": "Slide 2",
            "section": "01 • Introduction",
            "title": "The Problem & The Brain Mapper Solution",
            "time": "⏱️ Estimated Time: 1 minute",
            "cue": "👀 <b>What is on screen:</b> Three cards: 1) The Problem (Red), 2) Our Solution (Indigo), and 3) Practical Impact (Green).",
            "script": (
                "\"Let us start with the problem we see in our schools today.<br/><br/>"
                "When students take exams, teachers only see final marks—like 60% or 45%. But rich information inside their answer scripts is lost. Traditional machine learning models, called Knowledge Tracing, treat questions as black-box numbers. They can tell you <i>that</i> a student failed, but they cannot tell you <i>why</i>.<br/><br/>"
                "For example, did the student fail because they had trouble remembering intermediate equations? Or because they did not understand the tricky English wording?<br/><br/>"
                "This is where <b>Brain Mapper</b> comes in. We automatically score six fundamental cognitive skills—like Working Memory and Logical Reasoning—for every question using Large Language Models. Then, our custom model uses these cognitive scores to forecast future marks and show teachers exactly where students need help.\""
            ),
            "tip": "💡 <b>If asked:</b> 'Why not ask teachers to tag skills manually?' <i>Answer: Manual tagging is slow, subjective, and teachers don't have time to tag thousands of questions. AI automates this instantly.</i>",
        },
        {
            "num": "Slide 3",
            "section": "01 • Introduction",
            "title": "Research Aim & Three Core Objectives",
            "time": "⏱️ Estimated Time: 1 minute",
            "cue": "👀 <b>What is on screen:</b> Big purple aim card at the top, followed by 3 objective cards: RO1 (Extraction), RO2 (Modeling), and RO3 (Validation).",
            "script": (
                "\"Our main aim is to build a practical learning analytics framework that connects cognitive skills with student response histories to improve prediction accuracy and explain student thinking.<br/><br/>"
                "To achieve this, we have three clear research objectives:<br/>"
                "• <b>First (RO1)</b>, automatically extract and score six cognitive skills for every math question on a scale from 0 to 3 using multimodal LLMs.<br/>"
                "• <b>Second (RO2)</b>, develop a Cognitive-Aware Knowledge Tracing model—which we call CA-KT—that updates each student's cognitive mastery over time.<br/>"
                "• <b>Third (RO3)</b>, test our model against standard world benchmarks, evaluate it on real small-classroom groups, and build an offline exam system to collect local school data without internet.\""
            ),
            "tip": "💡 <b>Key takeaway:</b> Emphasize that the scope is decision-support for teachers, not automated grading.",
        },
        {
            "num": "Slide 4",
            "section": "02 • Progress",
            "title": "Current Progress & Completed Milestones",
            "time": "⏱️ Estimated Time: 1 minute",
            "cue": "👀 <b>What is on screen:</b> 4 large stat cards (7,652 Qs, 5.55M interactions, 6 models trained, 30/30 tests pass) + milestone boxes.",
            "script": (
                "\"Here is our current progress so far.<br/><br/>"
                "We have completed <b>100% of our question annotation</b>: all <b>7,652 mathematical questions</b> from the benchmark dataset are fully annotated with cognitive scores.<br/><br/>"
                "We prepared a massive dataset of <b>5.55 million student responses</b> across more than 18,000 students. We have successfully trained and tested <b>all six model architectures</b> on this complete dataset—including standard baselines like DKT, qDKT, and QIKT, as well as three variants of our new CA-KT model.<br/><br/>"
                "To make our research robust, we developed our own browser extension to automate data collection, and we also built the offline classroom exam server. All 30 automated tests across our Python and Node.js code are completely passing.\""
            ),
            "tip": "💡 <b>Highlight:</b> Emphasize that all 7,652 questions are 100% finished, not just a small demo sample.",
        },
        {
            "num": "Slide 5",
            "section": "03 • Related Work",
            "title": "Literature Summary & Research Gap",
            "time": "⏱️ Estimated Time: 1 minute",
            "cue": "👀 <b>What is on screen:</b> 3 comparison cards: Traditional KT vs. Cognitive Diagnosis vs. Brain Mapper, plus the bottom 'Research Gap' box.",
            "script": (
                "\"Looking at past research, existing systems fall into two separate categories:<br/><br/>"
                "On one side, we have <b>Traditional Knowledge Tracing</b> like DKT and QIKT. These models are great at tracking correctness over time, but they treat questions like meaningless IDs. They provide zero explanation of student cognitive skills.<br/><br/>"
                "On the other side, we have <b>Cognitive Diagnosis Models</b> like IRT. These models can measure student ability, but they rely on human experts to manually create what is called a Q-matrix. That is expensive, slow, and cannot scale to thousands of questions.<br/><br/>"
                "<b>Brain Mapper bridges this gap.</b> We use Multimodal AI to extract the cognitive matrix automatically, and feed it into our deep neural network. This gives educators both superior prediction accuracy and explainable cognitive profiles without manual labor.\""
            ),
            "tip": "💡 <b>Summary phrase:</b> 'Traditional models know THAT a student failed; cognitive models know WHY. Brain Mapper gives you both.'",
        },
        {
            "num": "Slide 6",
            "section": "04 • Methodology",
            "title": "Dataset Curation & 6-Skill Cognitive Extraction",
            "time": "⏱️ Estimated Time: 1 minute",
            "cue": "👀 <b>What is on screen:</b> Left card: XES3G5M benchmark & extension details. Right card: The 6 cognitive skills with their average scores.",
            "script": (
                "\"Now, let us examine our dataset and methodology.<br/><br/>"
                "We use the globally recognized <b>XES3G5M dataset</b> with English questions from ExRec. It contains over 18,000 students and 7,652 math questions, including more than 2,200 geometry questions that have visual diagrams.<br/><br/>"
                "To score these questions, we developed a custom browser extension that automated feeding each question and its diagram into an LLM. Every question is rated from 0 to 3 across six fundamental skills:<br/>"
                "• <b>Logical Reasoning</b> is the highest demand, averaging 2.46 out of 3.<br/>"
                "• <b>Working Memory</b> is second, averaging 2.30, because multi-step algebra requires holding equations in mind.<br/>"
                "• Followed by <b>Attention</b> for diagrams, <b>Language Processing</b> for word problems, <b>Critical Thinking</b>, and <b>Metacognition</b>.\""
            ),
            "tip": "💡 <b>Clarification:</b> The browser extension was our automated tool to collect annotations without paying commercial API costs.",
        },
        {
            "num": "Slide 7",
            "section": "05 • System Architecture",
            "title": "CA-KT Neural Network Architecture",
            "time": "⏱️ Estimated Time: 1 minute 15 seconds",
            "cue": "👀 <b>What is on screen:</b> High-resolution neural network architecture diagram showing inputs, Rasch decomposition, LSTM, attention, and IRT output.",
            "script": (
                "\"This slide presents the core technical novelty of our research: the <b>CA-KT Neural Network Architecture</b>.<br/><br/>"
                "It works in five connected stages:<br/>"
                "1. <b>Inputs:</b> We take the student's previous question, response, and 6-dimensional cognitive demand vector.<br/>"
                "2. <b>Rasch Item Decomposition:</b> Standard models fail on small classes because they try to memorize 7,000 question IDs. We decompose each question into shared concept clusters and cognitive vectors, modulated by a single scalar deviation factor. This completely stops question-ID overfitting.<br/>"
                "3. <b>Memory & Attention:</b> An LSTM encodes student learning history, and a 200-step causal attention module focuses on recent, relevant practice.<br/>"
                "4. <b>Cognitive Mastery & IRT:</b> The model computes an interpretable student mastery vector across all 6 skills, alongside student ability theta and question difficulty beta.<br/>"
                "5. <b>Output:</b> It predicts the probability of the student answering the next question correctly, while outputting a 6-axis cognitive radar profile for the teacher.\""
            ),
            "tip": "💡 <b>If asked:</b> 'What is the main innovation?' <i>Answer: Combining Rasch item decomposition with 6D cognitive vectors and causal attention, so the model learns concepts rather than memorizing question IDs.</i>",
        },
        {
            "num": "Slide 8",
            "section": "05 • System Architecture",
            "title": "Offline LAN Examination & Analytics Platform",
            "time": "⏱️ Estimated Time: 1 minute",
            "cue": "👀 <b>What is on screen:</b> Left: Offline LAN Wi-Fi network diagram with teacher laptop and student devices. Right: Key features card.",
            "script": (
                "\"To make sure our research works in real Sri Lankan schools, we also engineered the <b>BrainMapper Offline LAN Examination Platform</b>.<br/><br/>"
                "In many rural and government schools, internet connections are unstable or unavailable in computer rooms. Our platform solves this completely:<br/>"
                "• The teacher runs the BrainMapper virtual server on a normal laptop, connected to a standard Wi-Fi router or phone hotspot—<b>zero internet data is required</b>.<br/>"
                "• The server generates a unique QR code. Students simply point their phone or tablet camera at the QR code and log in using their assigned Student ID.<br/>"
                "• For exam security, answer keys are completely stripped from network packets so students cannot inspect answers. If a student's browser accidentally reloads, auto-drafts restore their progress instantly.<br/>"
                "This platform is ready to collect Phase 2 term-test data directly from Grade 10 and 11 classrooms.\""
            ),
            "tip": "💡 <b>Emphasize:</b> Practical feasibility. No school needs to pay for internet or expensive tablets; any browser on a local Wi-Fi router works.",
        },
        {
            "num": "Slide 9",
            "section": "06 • Preliminary Results",
            "title": "Full-Dataset Benchmark Results",
            "time": "⏱️ Estimated Time: 1 minute 15 seconds",
            "cue": "👀 <b>What is on screen:</b> Clustered column chart comparing DKT, qDKT, QIKT, and New CA-KT across Standard AUC, Fine-Tuned AUC, and From-Scratch AUC.",
            "script": (
                "\"Now, let us examine our experimental results on the full 5.55 million interaction dataset.<br/><br/>"
                "As you can see in the chart, our proposed <b>New CA-KT model ranks number one across all metrics</b>:<br/>"
                "• On completely unseen students in the standard benchmark, New CA-KT achieves an <b>AUC of 0.8119</b> and 82.5% accuracy, outperforming DKT, qDKT, and QIKT.<br/>"
                "• But the most dramatic improvement is shown in the yellow bars—<b>Classroom From-Scratch training</b> on 40 students. Standard models like qDKT collapse to an AUC of 0.4976, which is no better than a coin flip, because 40 students are not enough to learn 7,000 question IDs. New CA-KT achieves <b>0.6196 AUC</b>—a huge <b>12.2% increase</b> over qDKT.<br/>"
                "• When fine-tuning on a class's past history, CA-KT reaches <b>0.7640 AUC</b> with 80.9% accuracy.<br/>"
                "This proves that cognitive skills and concept clustering prevent models from overfitting on small classroom data.\""
            ),
            "tip": "💡 <b>Standout stat:</b> '12.2% AUC improvement on small 40-student classes.' Evaluators love seeing practical classroom improvements.",
        },
        {
            "num": "Slide 10",
            "section": "07 • Challenges & Solutions",
            "title": "Major Obstacles & How We Solved Them",
            "time": "⏱️ Estimated Time: 1 minute",
            "cue": "👀 <b>What is on screen:</b> 3 challenge-solution cards: 1) School Data Loss, 2) High API Costs, and 3) Small-Class Overfitting.",
            "script": (
                "\"During this project, we encountered three major practical challenges and engineered clear solutions for each:<br/><br/>"
                "1. <b>Initial School Data Collection:</b> When we visited schools, physical answer scripts had already been returned to students and lost. <i>Our solution:</i> We used the verified XES3G5M benchmark for model training, and built the offline LAN system so schools can collect Phase 2 data digitally.<br/><br/>"
                "2. <b>High Commercial LLM Costs:</b> Annotating 7,652 questions using paid multimodal APIs would have cost thousands of dollars or hit tight daily free limits. <i>Our solution:</i> We built a browser extension and local bridge server to annotate the complete dataset for free.<br/><br/>"
                "3. <b>Small-Class Overfitting:</b> Training deep neural networks on 40 students normally fails. <i>Our solution:</i> We developed Rasch item decomposition and 64 cognitive concept clusters, delivering state-of-the-art accuracy even on small cohorts.\""
            ),
            "tip": "💡 <b>Message:</b> Demonstrates proactive problem-solving, engineering resourcefulness, and perseverance.",
        },
        {
            "num": "Slide 11",
            "section": "08 & 09 • Future Work & Conclusion",
            "title": "Next Steps & Final Summary",
            "time": "⏱️ Estimated Time: 1 minute",
            "cue": "👀 <b>What is on screen:</b> Left card: 4 future work steps (Months 7–12). Right card: Conclusion. Bottom: Thank you & Q&A banner.",
            "script": (
                "\"To conclude, let us look at our next steps and final takeaways.<br/><br/>"
                "Over Months 7 to 12, our roadmap is focused on:<br/>"
                "• Connecting the trained CA-KT model weights directly into the BrainMapper web app so teachers can see live pre-quiz predictions.<br/>"
                "• Completing multi-LLM cross-validation with Gemini Pro.<br/>"
                "• Conducting Phase 2 classroom pilot tests in local Grade 10 and 11 classes.<br/>"
                "• Interviewing mathematics lecturers and teachers to validate the usefulness of our explainable cognitive profiles.<br/><br/>"
                "<b>In summary:</b> Brain Mapper proves that incorporating cognitive skills makes Knowledge Tracing more accurate, solves the small-classroom data bottleneck, and gives teachers meaningful diagnostic insights rather than black-box numbers.<br/><br/>"
                "Thank you very much for your time. We are now happy to take any questions!\""
            ),
            "tip": "💡 <b>Final impression:</b> End with confidence, thank the evaluators, and stand ready for the Q&A session.",
        },
    ]

    for item in slides_data:
        # Build a neat card table for each slide
        meta_text = f"<b>{item['num'].upper()}</b>  |  {item['section'].upper()}  |  {item['time']}"
        header_p = Paragraph(meta_text, slide_meta_style)
        title_p = Paragraph(item["title"], slide_hdr_style)
        cue_p = Paragraph(item["cue"], cue_style)
        script_p = Paragraph(item["script"], script_style)
        tip_p = Paragraph(item["tip"], tip_style)

        table_data = [
            [header_p],
            [title_p],
            [HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=6, spaceBefore=4)],
            [cue_p],
            [script_p],
            [HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#E2E8F0"), spaceAfter=4, spaceBefore=4)],
            [tip_p],
        ]

        t = Table(table_data, colWidths=[504])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 1.2, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ]
            )
        )

        story.append(KeepTogether([t, Spacer(1, 14)]))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated Speaker Notes PDF: {PDF_PATH} ({PDF_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    build_pdf()
