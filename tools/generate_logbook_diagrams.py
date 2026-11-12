"""
Generate crisp, publication-grade engineering & UI diagrams for the Brain Mapper Log Book.
Produces 4 PNG images matching the exact diagram slots in the handwritten log book.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path("docs/diagrams")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    """Load clean Windows TrueType font with fallback."""
    candidates = []
    if mono:
        candidates = [r"C:\Windows\Fonts\consolab.ttf" if bold else r"C:\Windows\Fonts\consola.ttf"]
    elif bold:
        candidates = [r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"]
    else:
        candidates = [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"]

    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    max_width_chars: int,
    font: ImageFont.FreeTypeFont,
    fill: str = "#2D3748",
    line_spacing: int = 8,
    align: str = "left",
) -> int:
    """Draw word-wrapped text and return final Y position."""
    lines = []
    for paragraph in text.split("\n"):
        if paragraph.strip() == "":
            lines.append("")
        else:
            lines.extend(textwrap.wrap(paragraph, width=max_width_chars))

    cur_y = y
    for line in lines:
        bbox = draw.textbbox((0, 0), line if line else "Ag", font=font)
        line_h = bbox[3] - bbox[1]
        if align == "center" and line:
            line_w = bbox[2] - bbox[0]
            draw.text((x - line_w // 2, cur_y), line, font=font, fill=fill)
        else:
            draw.text((x, cur_y), line, font=font, fill=fill)
        cur_y += line_h + line_spacing
    return cur_y


def draw_centered_text(draw: ImageDraw.ImageDraw, text: str, center_x: int, y: int, font: ImageFont.FreeTypeFont, fill: str) -> None:
    """Draw horizontally centered text."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((center_x - tw // 2, y), text, font=font, fill=fill)


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: str = "#2B6CB0",
    width: int = 5,
    head_len: int = 18,
    label: str | None = None,
    label_offset: tuple[int, int] = (0, -34),
) -> None:
    """Draw straight directional arrow with optional centered label pill."""
    x1, y1 = start
    x2, y2 = end
    draw.line([start, end], fill=color, width=width)

    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    p1 = (
        int(x2 - head_len * math.cos(angle - math.pi / 6)),
        int(y2 - head_len * math.sin(angle - math.pi / 6)),
    )
    p2 = (
        int(x2 - head_len * math.cos(angle + math.pi / 6)),
        int(y2 - head_len * math.sin(angle + math.pi / 6)),
    )
    draw.polygon([end, p1, p2], fill=color)

    if label:
        font_lbl = load_font(20, bold=True)
        mx = (x1 + x2) // 2 + label_offset[0]
        my = (y1 + y2) // 2 + label_offset[1]
        bbox = draw.textbbox((0, 0), label, font=font_lbl)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad_x, pad_y = 12, 8
        draw.rounded_rectangle(
            [mx - tw // 2 - pad_x, my - th // 2 - pad_y, mx + tw // 2 + pad_x, my + th // 2 + pad_y],
            radius=8,
            fill="#FFFFFF",
            outline=color,
            width=2,
        )
        draw.text((mx, my), label, font=font_lbl, fill=color, anchor="mm")


def draw_qr_graphic(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: str = "#1A202C") -> None:
    """Draw a recognizable stylized QR code block."""
    draw.rectangle([x, y, x + size, y + size], fill="#FFFFFF", outline="#CBD5E1", width=3)
    m = max(4, size // 18)
    inner_x = x + m
    inner_y = y + m
    cell = (size - 2 * m) // 9

    def finder(fx: int, fy: int):
        draw.rectangle([fx, fy, fx + 3 * cell, fy + 3 * cell], fill=color)
        draw.rectangle([fx + cell // 2, fy + cell // 2, fx + int(2.5 * cell), fy + int(2.5 * cell)], fill="#FFFFFF")
        draw.rectangle([fx + cell, fy + cell, fx + 2 * cell, fy + 2 * cell], fill=color)

    finder(inner_x, inner_y)
    finder(inner_x + 6 * cell, inner_y)
    finder(inner_x, inner_y + 6 * cell)

    # Deterministic data modules in remaining grid
    pattern = [
        (4, 0), (4, 2), (5, 1), (4, 4), (5, 4), (6, 4), (8, 4),
        (0, 4), (2, 4), (1, 5), (3, 5), (5, 6), (7, 5), (8, 6),
        (4, 7), (6, 7), (5, 8), (7, 8), (8, 8), (4, 5), (6, 5),
    ]
    for gx, gy in pattern:
        px = inner_x + gx * cell
        py = inner_y + gy * cell
        draw.rectangle([px + 1, py + 1, px + cell - 1, py + cell - 1], fill=color)


def create_diagram_1_llm_costs() -> Path:
    """Diagram 1: 4 API Cost Boxes (Gemini Cost, DeepSeek Cost, ChatGPT Cost, Groq Cost)."""
    W, H = 2000, 920
    img = Image.new("RGB", (W, H), "#F8FAFC")
    draw = ImageDraw.Draw(img)

    f_title = load_font(38, bold=True)
    f_sub = load_font(24)
    f_card_h = load_font(30, bold=True)
    f_cost = load_font(34, bold=True)
    f_body = load_font(22)
    f_badge = load_font(21, bold=True)

    # Title bar
    draw_centered_text(draw, "Estimated Commercial API Costs for 7,652 Questions", W // 2, 35, f_title, "#1A365D")
    draw_centered_text(
        draw,
        "Workload: 5,438 Text + 2,214 Visual Diagram Questions (2,459 PNGs) | ~8.8M Tokens",
        W // 2,
        88,
        f_sub,
        "#4A5568",
    )

    cards = [
        {
            "title": "Gemini Cost",
            "accent": "#1A73E8",
            "bg": "#EFF6FF",
            "cost": "~$1.50 - $3.50",
            "subcost": "Paid Tier / Free: 15 RPM",
            "bullets": [
                "• Free Tier Cap: 500 req/day",
                "• Paused at 980 Qs (slow)",
                "• Takes 16+ days on free tier",
                "• Batch API requires paid card",
            ],
            "status": "Hit Daily Quota Wall",
        },
        {
            "title": "DeepSeek Cost",
            "accent": "#4F46E5",
            "bg": "#EEF2FF",
            "cost": "~$1.40 - $2.60",
            "subcost": "Text-Only Token API",
            "bullets": [
                "• Cheap per 1M tokens",
                "• Requires billing top-up card",
                "• API lacked direct image upload",
                "• Cannot process 2,459 PNGs via API",
            ],
            "status": "No Vision PNG via API",
        },
        {
            "title": "ChatGPT Cost",
            "accent": "#10A37F",
            "bg": "#ECFDF5",
            "cost": "~$35 - $55 USD",
            "subcost": "GPT-4o Multimodal API",
            "bullets": [
                "• $2.50/1M in + $10/1M out tokens",
                "• Extra high vision image charges",
                "• Expensive for student budget",
                "• Requires credit card billing",
            ],
            "status": "Too Expensive",
        },
        {
            "title": "Groq Cost",
            "accent": "#EA580C",
            "bg": "#FFF7ED",
            "cost": "$0 (Strict Caps)",
            "subcost": "6,000 TPM Limit",
            "bullets": [
                "• Constant HTTP 429 errors",
                "• Only ~30 requests/minute",
                "• Tight tokens-per-minute cap",
                "• Poor multimodal batching",
            ],
            "status": "Severe Rate Limits",
        },
    ]

    card_w = 435
    card_h = 620
    gap = 40
    start_x = (W - (4 * card_w + 3 * gap)) // 2
    top_y = 155

    for idx, c in enumerate(cards):
        cx = start_x + idx * (card_w + gap)
        # Drop shadow
        draw.rounded_rectangle([cx + 6, top_y + 8, cx + card_w + 6, top_y + card_h + 8], radius=18, fill="#E2E8F0")
        # Card body
        draw.rounded_rectangle(
            [cx, top_y, cx + card_w, top_y + card_h],
            radius=18,
            fill="#FFFFFF",
            outline=c["accent"],
            width=4,
        )
        # Header band
        draw.rounded_rectangle([cx, top_y, cx + card_w, top_y + 88], radius=18, fill=c["accent"])
        draw.rectangle([cx, top_y + 50, cx + card_w, top_y + 88], fill=c["accent"])
        bbox_h = draw.textbbox((0, 0), c["title"], font=f_card_h)
        draw.text((cx + (card_w - (bbox_h[2] - bbox_h[0])) // 2, top_y + 24), c["title"], font=f_card_h, fill="#FFFFFF")

        # Cost highlight box
        draw.rounded_rectangle([cx + 24, top_y + 115, cx + card_w - 24, top_y + 225], radius=12, fill=c["bg"])
        bbox_c = draw.textbbox((0, 0), c["cost"], font=f_cost)
        draw.text((cx + (card_w - (bbox_c[2] - bbox_c[0])) // 2, top_y + 132), c["cost"], font=f_cost, fill=c["accent"])
        bbox_sc = draw.textbbox((0, 0), c["subcost"], font=f_body)
        draw.text((cx + (card_w - (bbox_sc[2] - bbox_sc[0])) // 2, top_y + 184), c["subcost"], font=f_body, fill="#4A5568")

        # Bullet items
        cur_y = top_y + 255
        for b in c["bullets"]:
            cur_y = draw_wrapped_text(draw, b, cx + 28, cur_y, max_width_chars=30, font=f_body, fill="#2D3748", line_spacing=8)
            cur_y += 10

        # Bottom limitation pill
        draw.rounded_rectangle(
            [cx + 30, top_y + card_h - 75, cx + card_w - 30, top_y + card_h - 24],
            radius=10,
            fill="#FEE2E2",
            outline="#EF4444",
            width=2,
        )
        bbox_st = draw.textbbox((0, 0), c["status"], font=f_badge)
        draw.text(
            (cx + (card_w - (bbox_st[2] - bbox_st[0])) // 2, top_y + card_h - 62),
            c["status"],
            font=f_badge,
            fill="#B91C1C",
        )

    # Bottom takeaway banner
    draw.rounded_rectangle([start_x, 808, W - start_x, 882], radius=12, fill="#1A365D")
    msg = "Conclusion: Commercial APIs were either too costly or blocked by limits -> Prompted our Zero-Cost Browser Extension Idea"
    bbox_m = draw.textbbox((0, 0), msg, font=f_sub)
    draw.text(((W - (bbox_m[2] - bbox_m[0])) // 2, 830), msg, font=f_sub, fill="#FFFFFF")

    out_path = OUT_DIR / "fig1_llm_api_costs.png"
    img.save(out_path, dpi=(300, 300))
    return out_path


def create_diagram_2_extension_arch() -> Path:
    """Diagram 2: Zero-Cost DeepSeek Browser Extension + Local Bridge Server Architecture."""
    W, H = 2240, 960
    img = Image.new("RGB", (W, H), "#F8FAFC")
    draw = ImageDraw.Draw(img)

    f_title = load_font(38, bold=True)
    f_sub = load_font(24)
    f_box_h = load_font(28, bold=True)
    f_body = load_font(22)
    f_mono = load_font(20, mono=True)

    draw_centered_text(draw, "Zero-Cost Automation Architecture (Browser Extension + Local Server)", W // 2, 32, f_title, "#1A365D")
    draw_centered_text(
        draw,
        "Automating DeepSeek Web Chat to annotate 7,652 multimodal questions at $0 API cost",
        W // 2,
        86,
        f_sub,
        "#4A5568",
    )

    # 4 horizontal component nodes with generous 190px arrow gaps
    box_w = 390
    box_h = 540
    y_top = 180
    xs = [55, 635, 1215, 1795]

    nodes = [
        {
            "title": "1. XES3G5M Dataset",
            "sub": "(Local Storage)",
            "accent": "#334155",
            "items": [
                "• questions.csv",
                "  (7,652 Math Qs)",
                "• 2,459 Real Diagram PNGs",
                "• Answer keys hidden",
                "  to avoid data leakage",
                "",
                "Output Saved:",
                "• deepseek_annotations.jsonl",
                "• state.json (Progress)",
            ],
        },
        {
            "title": "2. Local Bridge Server",
            "sub": "Python (127.0.0.1:8765)",
            "accent": "#0D9488",
            "items": [
                "• Serves next uncompleted Q",
                "• Streams PNG images",
                "  (/api/image?path=...)",
                "• Validates 6 skills (0-3)",
                "• Prevents duplicate saves",
                "• Handles Windows Win32 locks",
                "• Tracks team progress",
            ],
        },
        {
            "title": "3. Chrome Extension",
            "sub": "Manifest V3 Content Script",
            "accent": "#2563EB",
            "items": [
                "• Fetches Q from Bridge",
                "• Pastes prompt into chat",
                "• Uploads PNG diagrams via",
                "  HTML5 DataTransfer API",
                "• Clicks Send & waits cleanly",
                "• Strips <think> blocks",
                "• Extracts & returns JSON",
            ],
        },
        {
            "title": "4. DeepSeek Web Chat",
            "sub": "chat.deepseek.com ($0 Cost)",
            "accent": "#4F46E5",
            "items": [
                "• Frontier DeepSeek-R1 / V3",
                "• Reads problem + diagram",
                "• Evaluates 6 cognitive skills:",
                "  Attention, Working Mem,",
                "  Logic, Language, Critical,",
                "  and Metacognition",
                "• Outputs structured JSON",
            ],
        },
    ]

    for idx, n in enumerate(nodes):
        bx = xs[idx]
        draw.rounded_rectangle([bx + 6, y_top + 8, bx + box_w + 6, y_top + box_h + 8], radius=16, fill="#E2E8F0")
        draw.rounded_rectangle([bx, y_top, bx + box_w, y_top + box_h], radius=16, fill="#FFFFFF", outline=n["accent"], width=4)
        draw.rounded_rectangle([bx, y_top, bx + box_w, y_top + 100], radius=16, fill=n["accent"])
        draw.rectangle([bx, y_top + 60, bx + box_w, y_top + 100], fill=n["accent"])

        bh = draw.textbbox((0, 0), n["title"], font=f_box_h)
        draw.text((bx + (box_w - (bh[2] - bh[0])) // 2, y_top + 18), n["title"], font=f_box_h, fill="#FFFFFF")
        bs = draw.textbbox((0, 0), n["sub"], font=f_mono)
        draw.text((bx + (box_w - (bs[2] - bs[0])) // 2, y_top + 60), n["sub"], font=f_mono, fill="#E2E8F0")

        cy = y_top + 125
        for line in n["items"]:
            draw.text((bx + 22, cy), line, font=f_body, fill="#2D3748")
            cy += 40

    # Arrows between boxes
    # 1 <-> 2
    draw_arrow(draw, (xs[0] + box_w + 8, y_top + 205), (xs[1] - 8, y_top + 205), color="#0D9488", label="Read CSV/PNG", label_offset=(0, -34))
    draw_arrow(draw, (xs[1] - 8, y_top + 375), (xs[0] + box_w + 8, y_top + 375), color="#334155", label="Save JSONL", label_offset=(0, 34))

    # 2 <-> 3
    draw_arrow(draw, (xs[1] + box_w + 8, y_top + 205), (xs[2] - 8, y_top + 205), color="#2563EB", label="Next Q", label_offset=(0, -34))
    draw_arrow(draw, (xs[2] - 8, y_top + 375), (xs[1] + box_w + 8, y_top + 375), color="#0D9488", label="POST JSON", label_offset=(0, 34))

    # 3 <-> 4
    draw_arrow(draw, (xs[2] + box_w + 8, y_top + 205), (xs[3] - 8, y_top + 205), color="#4F46E5", label="Inject + PNG", label_offset=(0, -34))
    draw_arrow(draw, (xs[3] - 8, y_top + 375), (xs[2] + box_w + 8, y_top + 375), color="#2563EB", label="Scrape Output", label_offset=(0, 34))

    # Bottom Cross-Validation Callout Note
    draw.rounded_rectangle([55, 775, W - 55, 895], radius=14, fill="#EFF6FF", outline="#2563EB", width=3)
    draw.text(
        (90, 798),
        "Cross-Validation Extension (Built Later Using This Exact Architecture):",
        font=f_box_h,
        fill="#1E40AF",
    )
    draw.text(
        (90, 840),
        "• Adapted on Port 8767 for Google Gemini Web (500 text-based questions) to validate DeepSeek scores without needing manual human grading.",
        font=f_sub,
        fill="#1E3A8A",
    )

    out_path = OUT_DIR / "fig2_deepseek_extension_arch.png"
    img.save(out_path, dpi=(300, 300))
    return out_path


def create_diagram_3_lan_qr_arch() -> Path:
    """Diagram 3: Offline LAN Examination Network & QR Login Architecture."""
    W, H = 2120, 980
    img = Image.new("RGB", (W, H), "#F8FAFC")
    draw = ImageDraw.Draw(img)

    f_title = load_font(38, bold=True)
    f_sub = load_font(24)
    f_box_h = load_font(28, bold=True)
    f_body = load_font(22)
    f_mono = load_font(22, bold=True, mono=True)

    draw_centered_text(draw, "Offline LAN Examination Network & QR Login Architecture", W // 2, 30, f_title, "#1A365D")
    draw_centered_text(
        draw,
        "Zero Internet Required: Wireless Router / Mobile Hotspot + Instructor PC Server + QR Scan",
        W // 2,
        82,
        f_sub,
        "#4A5568",
    )

    # Top Center Hub: Router / Mobile Hotspot
    hub_w, hub_h = 680, 140
    hub_x = (W - hub_w) // 2
    hub_y = 145
    draw.rounded_rectangle([hub_x + 5, hub_y + 6, hub_x + hub_w + 5, hub_y + hub_h + 6], radius=18, fill="#CBD5E1")
    draw.rounded_rectangle([hub_x, hub_y, hub_x + hub_w, hub_y + hub_h], radius=18, fill="#0D9488", outline="#0F766E", width=4)
    draw_centered_text(draw, "Wireless Router / Mobile Hotspot", W // 2, hub_y + 22, load_font(32, bold=True), "#FFFFFF")
    draw_centered_text(draw, "Shared Local Wi-Fi Network (No Internet Required)", W // 2, hub_y + 78, f_sub, "#CCFBF1")

    # Left Box: Instructor PC (Virtual Server + QR Generator)
    lx, ly, lw, lh = 70, 385, 800, 520
    draw.rounded_rectangle([lx + 6, ly + 8, lx + lw + 6, ly + lh + 8], radius=18, fill="#E2E8F0")
    draw.rounded_rectangle([lx, ly, lx + lw, ly + lh], radius=18, fill="#FFFFFF", outline="#1A365D", width=4)
    draw.rounded_rectangle([lx, ly, lx + lw, ly + 85], radius=18, fill="#1A365D")
    draw.rectangle([lx, ly + 50, lx + lw, ly + 85], fill="#1A365D")
    draw.text((lx + 40, ly + 22), "Instructor's PC (Hosts Virtual Server)", font=f_box_h, fill="#FFFFFF")

    draw.text((lx + 35, ly + 112), "• Runs Electron + Express QuizServer", font=f_body, fill="#2D3748")
    draw.text((lx + 35, ly + 150), "• Automatically detects local LAN IP:", font=f_body, fill="#2D3748")
    draw.rounded_rectangle([lx + 55, ly + 190, lx + 430, ly + 242], radius=8, fill="#EDF2F7", outline="#94A3B8", width=2)
    draw.text((lx + 75, ly + 202), "http://192.168.1.5:3000", font=f_mono, fill="#1E40AF")

    draw.text((lx + 35, ly + 272), "• Wraps IP link into dynamic QR Code", font=f_body, fill="#2D3748")
    draw.text((lx + 35, ly + 312), "• Manages Quiz Creation & Question Bank", font=f_body, fill="#2D3748")
    draw.text((lx + 35, ly + 352), "• Collects live student responses & times", font=f_body, fill="#2D3748")
    draw.text((lx + 35, ly + 392), "• No student app installation needed!", font=load_font(22, bold=True), fill="#0D9488")

    # QR Code inside Instructor box (right side)
    qr_x = lx + 520
    qr_y = ly + 145
    draw_qr_graphic(draw, qr_x, qr_y, 230, color="#1A365D")
    draw.text((qr_x + 35, qr_y + 242), "Scan to Join!", font=load_font(24, bold=True), fill="#1A365D")

    # Right Box: Students / Clients in Same LAN (380px center gap between boxes!)
    rx, ry, rw, rh = 1250, 385, 800, 520
    draw.rounded_rectangle([rx + 6, ry + 8, rx + rw + 6, ry + rh + 8], radius=18, fill="#E2E8F0")
    draw.rounded_rectangle([rx, ry, rx + rw, ry + rh], radius=18, fill="#FFFFFF", outline="#4A6BFD", width=4)
    draw.rounded_rectangle([rx, ry, rx + rw, ry + 85], radius=18, fill="#4A6BFD")
    draw.rectangle([rx, ry + 50, rx + rw, ry + 85], fill="#4A6BFD")
    draw.text((rx + 40, ry + 22), "Student Devices (Clients on Same LAN)", font=f_box_h, fill="#FFFFFF")

    # 3 Student device mini-cards inside right box
    devices = ["Student 1 (Phone)", "Student 2 (Tablet)", "Student 3 (Laptop)"]
    for i, dev in enumerate(devices):
        dx = rx + 35 + i * 250
        dy = ry + 115
        draw.rounded_rectangle([dx, dy, dx + 230, dy + 150], radius=12, fill="#EFF6FF", outline="#93C5FD", width=2)
        draw.text((dx + 18, dy + 16), dev, font=load_font(21, bold=True), fill="#1E40AF")
        draw.text((dx + 18, dy + 58), "1. Join Wi-Fi LAN", font=load_font(19), fill="#334155")
        draw.text((dx + 18, dy + 88), "2. Scan QR Code", font=load_font(19), fill="#334155")
        draw.text((dx + 18, dy + 118), "3. Open Exam UI", font=load_font(19), fill="#0D9488")

    # Step-by-step login box at bottom of Student side
    draw.rounded_rectangle([rx + 35, ry + 295, rx + rw - 35, ry + 485], radius=12, fill="#F0FDF4", outline="#10B981", width=2)
    draw.text((rx + 55, ry + 315), "How Students Log In Without Typing an IP:", font=load_font(24, bold=True), fill="#065F46")
    draw.text((rx + 55, ry + 358), "1. Student opens phone camera and scans Instructor's QR code.", font=f_body, fill="#064E3B")
    draw.text((rx + 55, ry + 396), "2. Browser automatically opens Instructor's virtual server URL.", font=f_body, fill="#064E3B")
    draw.text((rx + 55, ry + 434), "3. Student enters Name & takes the quiz immediately over LAN.", font=f_body, fill="#064E3B")

    # Network Lines from Hub to Instructor and Student Side
    draw_arrow(draw, (hub_x + 150, hub_y + hub_h), (lx + lw // 2, ly - 8), color="#0D9488", label="Host IP Bound", label_offset=(-145, -18))
    draw_arrow(draw, (hub_x + hub_w - 150, hub_y + hub_h), (rx + rw // 2, ry - 8), color="#4A6BFD", label="Wi-Fi Clients", label_offset=(145, -18))

    # Direct QR & Response communication arrows between Instructor and Students
    draw_arrow(draw, (lx + lw + 10, ly + 220), (rx - 10, ry + 220), color="#1A365D", label="QR Login Link", label_offset=(0, -34))
    draw_arrow(draw, (rx - 10, ry + 390), (lx + lw + 10, ly + 390), color="#4A6BFD", label="Quiz Answers", label_offset=(0, 34))

    out_path = OUT_DIR / "fig3_lan_network_qr_arch.png"
    img.save(out_path, dpi=(300, 300))
    return out_path


def create_diagram_4_frontend_interfaces() -> Path:
    """Diagram 4: Main Frontend Interfaces (Figma Design -> QR Connect, Quiz Creator, Student View)."""
    W, H = 2100, 960
    img = Image.new("RGB", (W, H), "#F8FAFC")
    draw = ImageDraw.Draw(img)

    f_title = load_font(38, bold=True)
    f_sub = load_font(24)
    f_win_h = load_font(23, bold=True)
    f_ui_h = load_font(24, bold=True)
    f_ui_b = load_font(20)
    f_ui_s = load_font(18)

    draw_centered_text(draw, "Main Frontend Interfaces (Designed in Figma & Built Components)", W // 2, 30, f_title, "#1A365D")
    draw_centered_text(
        draw,
        "Implemented Modules: User Connecting & QR Host + Quiz Creation Wizard (Under Active Development)",
        W // 2,
        84,
        f_sub,
        "#4A5568",
    )

    win_w = 620
    win_h = 700
    gap = 50
    start_x = (W - (3 * win_w + 2 * gap)) // 2
    top_y = 145

    def draw_window_frame(x: int, y: int, title: str, url: str, tag: str, tag_color: str):
        draw.rounded_rectangle([x + 6, y + 8, x + win_w + 6, y + win_h + 8], radius=16, fill="#CBD5E1")
        draw.rounded_rectangle([x, y, x + win_w, y + win_h], radius=16, fill="#FFFFFF", outline="#94A3B8", width=3)
        # Browser bar
        draw.rounded_rectangle([x, y, x + win_w, y + 54], radius=16, fill="#1E293B")
        draw.rectangle([x, y + 32, x + win_w, y + 54], fill="#1E293B")
        # Traffic lights
        draw.ellipse([x + 18, y + 19, x + 32, y + 33], fill="#EF4444")
        draw.ellipse([x + 40, y + 19, x + 54, y + 33], fill="#F59E0B")
        draw.ellipse([x + 62, y + 19, x + 76, y + 33], fill="#10B981")
        # URL pill
        draw.rounded_rectangle([x + 100, y + 10, x + win_w - 140, y + 44], radius=8, fill="#334155")
        draw.text((x + 115, y + 16), url, font=f_ui_s, fill="#E2E8F0")
        # Status tag
        draw.rounded_rectangle([x + win_w - 130, y + 11, x + win_w - 14, y + 43], radius=8, fill=tag_color)
        draw.text((x + win_w - 120, y + 16), tag, font=load_font(17, bold=True), fill="#FFFFFF")
        # App header banner (#4a6bfd from QuizServer CSS!)
        draw.rectangle([x + 3, y + 54, x + win_w - 3, y + 118], fill="#4A6BFD")
        draw.text((x + 25, y + 72), title, font=f_win_h, fill="#FFFFFF")

    # 1. Screen 1: User Connecting Part (Instructor QR Host)
    x1 = start_x
    draw_window_frame(x1, top_y, "QuizServer Admin - Connect", "localhost:3000/admin", "Built", "#0D9488")
    # Connect Here Card
    draw.rounded_rectangle([x1 + 25, top_y + 140, x1 + win_w - 25, top_y + 465], radius=12, fill="#F8FAFC", outline="#CBD5E1", width=2)
    draw.text((x1 + 45, top_y + 158), "Students: Connect Here", font=f_ui_h, fill="#1A365D")
    draw_qr_graphic(draw, x1 + 65, top_y + 205, 195, color="#1A202C")
    draw.text((x1 + 290, top_y + 225), "Local Server Link:", font=load_font(20, bold=True), fill="#475569")
    draw.rounded_rectangle([x1 + 290, top_y + 260, x1 + win_w - 45, top_y + 305], radius=8, fill="#E0E7FF")
    draw.text((x1 + 305, top_y + 271), "http://192.168.1.5:3000", font=load_font(20, bold=True, mono=True), fill="#4A6BFD")
    draw.text((x1 + 290, top_y + 328), "Scan QR on any phone", font=f_ui_b, fill="#334155")
    draw.text((x1 + 290, top_y + 358), "or tablet on same Wi-Fi.", font=f_ui_b, fill="#334155")
    # Connected counter badge
    draw.rounded_rectangle([x1 + 25, top_y + 488, x1 + win_w - 25, top_y + 560], radius=12, fill="#ECFDF5", outline="#10B981", width=2)
    draw.text((x1 + 45, top_y + 510), "Connected Participants:  28 Students Online", font=load_font(22, bold=True), fill="#065F46")
    # Action button
    draw.rounded_rectangle([x1 + 25, top_y + 585, x1 + win_w - 25, top_y + 650], radius=10, fill="#4A6BFD")
    draw.text((x1 + 195, top_y + 603), "+ Open Quiz Creator", font=load_font(22, bold=True), fill="#FFFFFF")

    # 2. Screen 2: Quiz Creating Part
    x2 = start_x + win_w + gap
    draw_window_frame(x2, top_y, "Create Quiz - QuizServer", "localhost:3000/create", "Built", "#0D9488")
    draw.text((x2 + 28, top_y + 138), "Quiz Title:", font=load_font(19, bold=True), fill="#334155")
    draw.rounded_rectangle([x2 + 28, top_y + 168, x2 + win_w - 28, top_y + 212], radius=8, fill="#F8FAFC", outline="#CBD5E1", width=2)
    draw.text((x2 + 42, top_y + 178), "Grade 10 Term Test - Algebra Practice", font=f_ui_b, fill="#1E293B")

    draw.text((x2 + 28, top_y + 228), "Timer Settings:  [ 30 Minutes ]   Mode: [ Offline LAN ]", font=f_ui_s, fill="#475569")

    # Question Builder card
    draw.rounded_rectangle([x2 + 28, top_y + 268, x2 + win_w - 28, top_y + 575], radius=12, fill="#F8FAFC", outline="#93C5FD", width=2)
    draw.text((x2 + 45, top_y + 284), "Question 1 (Multiple Choice)", font=load_font(21, bold=True), fill="#1E40AF")
    draw.rounded_rectangle([x2 + 45, top_y + 322, x2 + win_w - 45, top_y + 375], radius=6, fill="#FFFFFF", outline="#CBD5E1", width=2)
    draw.text((x2 + 58, top_y + 336), "If 3x + 4 = 19, find the value of x.", font=f_ui_b, fill="#1E293B")

    opts = ["(A) x = 3", "(B) x = 5  [Correct]", "(C) x = 7", "(D) x = 15"]
    oy = top_y + 392
    for opt in opts:
        fill_bg = "#DCFCE7" if "Correct" in opt else "#FFFFFF"
        out_c = "#16A34A" if "Correct" in opt else "#CBD5E1"
        draw.rounded_rectangle([x2 + 45, oy, x2 + win_w - 45, oy + 36], radius=6, fill=fill_bg, outline=out_c, width=2)
        draw.text((x2 + 60, oy + 5), opt, font=f_ui_s, fill="#1E293B")
        oy += 44

    # Bottom buttons
    draw.rounded_rectangle([x2 + 28, top_y + 595, x2 + 295, top_y + 655], radius=10, fill="#E2E8F0")
    draw.text((x2 + 72, top_y + 612), "+ Add Question", font=load_font(21, bold=True), fill="#334155")
    draw.rounded_rectangle([x2 + 320, top_y + 595, x2 + win_w - 28, top_y + 655], radius=10, fill="#10B981")
    draw.text((x2 + 395, top_y + 612), "Save & Publish", font=load_font(21, bold=True), fill="#FFFFFF")

    # 3. Screen 3: Student Join & Exam View (Figma UI)
    x3 = start_x + 2 * (win_w + gap)
    draw_window_frame(x3, top_y, "Join Quiz - Student View", "192.168.1.5:3000", "Built", "#0D9488")
    # Welcome / Name pill
    draw.rounded_rectangle([x3 + 28, top_y + 138, x3 + win_w - 28, top_y + 215], radius=10, fill="#EFF6FF", outline="#93C5FD", width=2)
    draw.text((x3 + 45, top_y + 148), "Welcome! Joined via QR Code", font=load_font(20, bold=True), fill="#1E40AF")
    draw.text((x3 + 45, top_y + 180), "Student Name: Kasun Perera  |  Time Left: 24:10", font=f_ui_s, fill="#334155")

    # Active Question display
    draw.rounded_rectangle([x3 + 28, top_y + 238, x3 + win_w - 28, top_y + 570], radius=12, fill="#FFFFFF", outline="#CBD5E1", width=2)
    draw.text((x3 + 45, top_y + 255), "Question 1 of 20", font=load_font(19, bold=True), fill="#64748B")
    draw.text((x3 + 45, top_y + 290), "If 3x + 4 = 19, find the value of x.", font=load_font(23, bold=True), fill="#1A202C")

    s_opts = ["A)  x = 3", "B)  x = 5", "C)  x = 7", "D)  x = 15"]
    sy = top_y + 345
    for idx_o, s_opt in enumerate(s_opts):
        is_sel = idx_o == 1
        bg = "#E0E7FF" if is_sel else "#F8FAFC"
        bd = "#4A6BFD" if is_sel else "#CBD5E1"
        draw.rounded_rectangle([x3 + 45, sy, x3 + win_w - 45, sy + 44], radius=8, fill=bg, outline=bd, width=3 if is_sel else 2)
        draw.text((x3 + 65, sy + 10), s_opt, font=load_font(20, bold=is_sel), fill="#1E293B")
        sy += 54

    draw.rounded_rectangle([x3 + 28, top_y + 595, x3 + win_w - 28, top_y + 655], radius=10, fill="#4A6BFD")
    draw.text((x3 + 205, top_y + 612), "Submit Answer ->", font=load_font(22, bold=True), fill="#FFFFFF")

    # Note at bottom
    draw_centered_text(
        draw,
        "Note: Main UI screens designed in Figma. User Connecting & Quiz Creation parts implemented; CA-KT analytics in Phase 2.",
        W // 2,
        882,
        load_font(21, bold=True),
        "#475569",
    )

    out_path = OUT_DIR / "fig4_frontend_interfaces.png"
    img.save(out_path, dpi=(300, 300))
    return out_path


def main():
    p1 = create_diagram_1_llm_costs()
    print("Generated:", p1)
    p2 = create_diagram_2_extension_arch()
    print("Generated:", p2)
    p3 = create_diagram_3_lan_qr_arch()
    print("Generated:", p3)
    p4 = create_diagram_4_frontend_interfaces()
    print("Generated:", p4)


if __name__ == "__main__":
    main()
