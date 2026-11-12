"""
Generate a publication-grade Neural Network Architecture diagram for CAKT
(Cognitive-Aware Knowledge Tracing) saved to docs/diagrams/cakt_neural_network_arch.png
"""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


OUT_PATH = Path(r"d:\Brain Mapper\docs\diagrams\cakt_neural_network_arch.png")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# 2400 x 1350 (16:9 widescreen high-res)
W, H = 2400, 1350
img = Image.new("RGBA", (W, H), (248, 250, 252, 255))  # Slate-50 background
draw = ImageDraw.Draw(img)

# Try loading standard Windows TrueType fonts, fallback to default
def get_font(size: int, bold: bool = False):
    font_names = [
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\calibri.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
    ]
    if bold:
        font_names = [
            "C:\\Windows\\Fonts\\segoeuib.ttf",
            "C:\\Windows\\Fonts\\calibrib.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf",
        ]
    for fn in font_names:
        if Path(fn).exists():
            try:
                return ImageFont.truetype(fn, size)
            except Exception:
                pass
    return ImageFont.load_default()

f_title = get_font(42, bold=True)
f_subtitle = get_font(24, bold=False)
f_sec = get_font(26, bold=True)
f_box_title = get_font(23, bold=True)
f_box_sub = get_font(18, bold=False)
f_tensor = get_font(19, bold=True)
f_tag = get_font(16, bold=True)

# Color constants
CLR_BG = (248, 250, 252)
CLR_NAVY = (15, 23, 42)
CLR_MUTED = (100, 116, 139)
CLR_LINE = (148, 163, 184)
CLR_BORDER = (203, 213, 225)

# Module Palette
M_BLUE = {"fill": (239, 246, 255), "border": (59, 130, 246), "header": (29, 78, 216), "tag": (219, 234, 254)}
M_INDIGO = {"fill": (238, 242, 255), "border": (99, 102, 241), "header": (67, 56, 202), "tag": (224, 231, 255)}
M_VIOLET = {"fill": (245, 243, 255), "border": (139, 92, 246), "header": (109, 40, 217), "tag": (237, 233, 254)}
M_TEAL = {"fill": (240, 253, 250), "border": (20, 184, 166), "header": (15, 118, 110), "tag": (204, 251, 241)}
M_EMERALD = {"fill": (236, 253, 245), "border": (16, 185, 129), "header": (4, 120, 87), "tag": (209, 250, 229)}
M_AMBER = {"fill": (254, 252, 232), "border": (245, 158, 11), "header": (180, 83, 9), "tag": (254, 243, 199)}
M_ROSE = {"fill": (255, 241, 242), "border": (244, 63, 94), "header": (190, 18, 60), "tag": (255, 228, 230)}

def round_rect(xy, radius, fill, outline, width=2):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

def draw_arrow(x1, y1, x2, y2, color=CLR_LINE, width=3, arrowhead=10):
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    if x1 == x2: # vertical
        if y2 > y1:
            draw.polygon([(x2, y2), (x2 - arrowhead, y2 - arrowhead), (x2 + arrowhead, y2 - arrowhead)], fill=color)
        else:
            draw.polygon([(x2, y2), (x2 - arrowhead, y2 + arrowhead), (x2 + arrowhead, y2 + arrowhead)], fill=color)
    elif y1 == y2: # horizontal
        if x2 > x1:
            draw.polygon([(x2, y2), (x2 - arrowhead, y2 - arrowhead), (x2 - arrowhead, y2 + arrowhead)], fill=color)
        else:
            draw.polygon([(x2, y2), (x2 + arrowhead, y2 - arrowhead), (x2 + arrowhead, y2 + arrowhead)], fill=color)

# ----------------- HEADER -----------------
draw.text((70, 45), "CA-KT: Cognitive-Aware Knowledge Tracing Neural Network Architecture", font=f_title, fill=CLR_NAVY)
draw.text((70, 100), "Rasch Concept-Cognitive Decomposition  |  Causal Time-Decayed Attention  |  Cognitive Mastery Profiling  |  Cognitive-IRT Diagnostic Head", font=f_subtitle, fill=CLR_MUTED)
draw.line([(70, 140), (W - 70, 140)], fill=CLR_BORDER, width=2)

# ----------------- 5 MAIN VERTICAL COLUMNS -----------------
# 1. Inputs & Feature Encoders (left = 70, width = 410)
# 2. Rasch Item & Cognitive Fusion (left = 520, width = 430)
# 3. Knowledge Acquisition & Attention (left = 990, width = 450)
# 4. Cognitive Mastery & IRT Estimators (left = 1480, width = 440)
# 5. Diagnostic Output & Objectives (left = 1960, width = 370)

col1_x, col1_w = 70, 410
col2_x, col2_w = 520, 430
col3_x, col3_w = 990, 450
col4_x, col4_w = 1480, 440
col5_x, col5_w = 1960, 370

# Column Headers
def col_header(x, w, title, color_set):
    round_rect((x, 160, x + w, 205), radius=8, fill=color_set["fill"], outline=color_set["border"], width=2)
    draw.text((x + 18, 170), title, font=f_sec, fill=color_set["header"])

col_header(col1_x, col1_w, "1. Multimodal Inputs (t, t+1)", M_BLUE)
col_header(col2_x, col2_w, "2. Rasch Cognitive Item", M_INDIGO)
col_header(col3_x, col3_w, "3. Memory & Attention", M_VIOLET)
col_header(col4_x, col4_w, "4. Cognitive IRT & Mastery", M_TEAL)
col_header(col5_x, col5_w, "5. Outputs & Loss", M_EMERALD)

# ----------------- COLUMN 1: INPUTS -----------------
# Box 1A: Question & Concept
b1a_y = 230
round_rect((col1_x, b1a_y, col1_x + col1_w, b1a_y + 190), radius=10, fill=(255, 255, 255), outline=CLR_BORDER, width=2)
draw.text((col1_x + 20, b1a_y + 15), "Question & Concept Inputs", font=f_box_title, fill=CLR_NAVY)
draw.text((col1_x + 20, b1a_y + 50), "• Question ID:  q_t , q_{t+1}  ∈ {1 .. 7,652}\n• Knowledge Concept / Cluster:  c_t , c_{t+1}\n  (64 K-Means Demand-Clustered Groups)", font=f_box_sub, fill=CLR_MUTED)
round_rect((col1_x + 20, b1a_y + 135, col1_x + 230, b1a_y + 172), radius=6, fill=M_BLUE["tag"], outline=M_BLUE["border"], width=1)
draw.text((col1_x + 30, b1a_y + 143), "Concept Emb: e_c ∈ R^128", font=f_tensor, fill=M_BLUE["header"])

# Box 1B: 6D Cognitive Demands
b1b_y = 445
round_rect((col1_x, b1b_y, col1_x + col1_w, b1b_y + 245), radius=10, fill=(255, 255, 255), outline=CLR_BORDER, width=2)
draw.text((col1_x + 20, b1b_y + 15), "6-Skill Cognitive Demands", font=f_box_title, fill=CLR_NAVY)
draw.text((col1_x + 20, b1b_y + 48), "• LLM-Annotated 0–3 Normalized Demand:\n  [Attn, W-Mem, Logic, Lang, Crit, Meta]\n• Linear(6 → 64) + GELU\n• Signed Cognitive Outcome:\n  [cog · r_t  ||  cog · (1 - r_t)]", font=f_box_sub, fill=CLR_MUTED)
round_rect((col1_x + 20, b1b_y + 190, col1_x + 230, b1b_y + 227), radius=6, fill=M_INDIGO["tag"], outline=M_INDIGO["border"], width=1)
draw.text((col1_x + 30, b1b_y + 198), "Cog Proj: v_cog ∈ R^64", font=f_tensor, fill=M_INDIGO["header"])

# Box 1C: Student Response History
b1c_y = 715
round_rect((col1_x, b1c_y, col1_x + col1_w, b1c_y + 160), radius=10, fill=(255, 255, 255), outline=CLR_BORDER, width=2)
draw.text((col1_x + 20, b1c_y + 15), "Student Response r_t", font=f_box_title, fill=CLR_NAVY)
draw.text((col1_x + 20, b1c_y + 50), "• Binary Correctness: r_t ∈ {0, 1}\n• Response Embedding: e_r ∈ R^128\n• Student Optional Bias: s_{idx} ∈ R^1", font=f_box_sub, fill=CLR_MUTED)
round_rect((col1_x + 20, b1c_y + 115, col1_x + 230, b1c_y + 150), radius=6, fill=M_TEAL["tag"], outline=M_TEAL["border"], width=1)
draw.text((col1_x + 30, b1c_y + 122), "Resp Emb: e_r ∈ R^128", font=f_tensor, fill=M_TEAL["header"])

# ----------------- COLUMN 2: RASCH COGNITIVE ITEM -----------------
b2_y = 230
round_rect((col2_x, b2_y, col2_x + col2_w, b2_y + 645), radius=10, fill=(255, 255, 255), outline=M_INDIGO["border"], width=2)
draw.text((col2_x + 20, b2_y + 18), "Rasch Concept-Cognitive Decomposition", font=f_box_title, fill=M_INDIGO["header"])
draw.text((col2_x + 20, b2_y + 55), "Overcomes Question ID Memorization & Overfitting", font=f_box_sub, fill=CLR_MUTED)

# Equation box 1
round_rect((col2_x + 20, b2_y + 95, col2_x + col2_w - 20, b2_y + 205), radius=8, fill=M_INDIGO["fill"], outline=M_INDIGO["border"], width=1)
draw.text((col2_x + 30, b2_y + 105), "1. Base Concept-Cognitive Representation:", font=f_tag, fill=M_INDIGO["header"])
draw.text((col2_x + 30, b2_y + 130), "e_base = W_base [ e_c || v_cog ]", font=f_tensor, fill=CLR_NAVY)
draw.text((col2_x + 30, b2_y + 165), "Anchors problem in shared math concepts & 6D cognitive demands.", font=f_box_sub, fill=CLR_MUTED)

# Equation box 2
round_rect((col2_x + 20, b2_y + 225, col2_x + col2_w - 20, b2_y + 355), radius=8, fill=M_INDIGO["fill"], outline=M_INDIGO["border"], width=1)
draw.text((col2_x + 30, b2_y + 235), "2. Question-Specific Variation Vector:", font=f_tag, fill=M_INDIGO["header"])
draw.text((col2_x + 30, b2_y + 260), "d_var = W_var [ d_c || v_cog_diff ]", font=f_tensor, fill=CLR_NAVY)
draw.text((col2_x + 30, b2_y + 295), "Captures difficulty variation across concept\nand cognitive demand nuances.", font=f_box_sub, fill=CLR_MUTED)

# Equation box 3
round_rect((col2_x + 20, b2_y + 375, col2_x + col2_w - 20, b2_y + 505), radius=8, fill=M_INDIGO["fill"], outline=M_INDIGO["border"], width=1)
draw.text((col2_x + 30, b2_y + 385), "3. Scalar Rasch Scaling & Item Composition:", font=f_tag, fill=M_INDIGO["header"])
draw.text((col2_x + 30, b2_y + 410), "e_q = e_base + μ_q · d_var", font=f_tensor, fill=CLR_NAVY)
draw.text((col2_x + 30, b2_y + 445), "μ_q ∈ R^1: Question deviation scalar with L2 penalty\ne_q ∈ R^128: Final Item Representation", font=f_box_sub, fill=CLR_MUTED)

# Resulting tensor
round_rect((col2_x + 20, b2_y + 525, col2_x + col2_w - 20, b2_y + 625), radius=8, fill=M_EMERALD["fill"], outline=M_EMERALD["border"], width=1)
draw.text((col2_x + 30, b2_y + 535), "Generalization Guarantee:", font=f_tag, fill=M_EMERALD["header"])
draw.text((col2_x + 30, b2_y + 565), "• Works on unseen questions & small 40-student classes.\n• Avoids learning 7,652 free lookup weights.", font=f_box_sub, fill=CLR_NAVY)

# ----------------- COLUMN 3: MEMORY & ATTENTION -----------------
b3_y = 230
round_rect((col3_x, b3_y, col3_x + col3_w, b3_y + 645), radius=10, fill=(255, 255, 255), outline=M_VIOLET["border"], width=2)
draw.text((col3_x + 20, b3_y + 18), "Knowledge Acquisition & Attention", font=f_box_title, fill=M_VIOLET["header"])

# Step 3A: Input fusion + LSTM
b3a_y = b3_y + 55
round_rect((col3_x + 20, b3a_y, col3_x + col3_w - 20, b3a_y + 240), radius=8, fill=M_VIOLET["fill"], outline=M_VIOLET["border"], width=1)
draw.text((col3_x + 30, b3a_y + 12), "Sequential Interaction Encoder (LSTM):", font=f_tag, fill=M_VIOLET["header"])
draw.text((col3_x + 30, b3a_y + 38), "x_t = [ e_q || e_c || e_r || v_cog || v_inter ]", font=f_tensor, fill=CLR_NAVY)
draw.text((col3_x + 30, b3a_y + 70), "acq_in = ReLU(Linear(x_t))  ∈ R^128\nh_t = LSTM(acq_in, h_{t-1}) ∈ R^128", font=f_tensor, fill=M_VIOLET["header"])
draw.text((col3_x + 30, b3a_y + 130), "• Encodes student's step-by-step math journey.\n• Tracks both concept mastery & cognitive load.", font=f_box_sub, fill=CLR_MUTED)

# Step 3B: Causal Time-Decayed Attention
b3b_y = b3_y + 315
round_rect((col3_x + 20, b3b_y, col3_x + col3_w - 20, b3b_y + 305), radius=8, fill=M_VIOLET["fill"], outline=M_VIOLET["border"], width=1)
draw.text((col3_x + 30, b3b_y + 12), "Causal Time-Decayed Cognitive Attention:", font=f_tag, fill=M_VIOLET["header"])
draw.text((col3_x + 30, b3b_y + 38), "Q = W_q [ e_{c, t+1} || v_{cog, t+1} ]\nK = W_k [ e_{c, s} || v_{cog, s} ]\nV = W_v [ h_s || e_{r, s} ]", font=f_tensor, fill=CLR_NAVY)
draw.text((col3_x + 30, b3b_y + 130), "Score = (Q K^T) / sqrt(d)  -  γ · log(1 + Δt)", font=f_tensor, fill=M_ROSE["header"])
draw.text((col3_x + 30, b3b_y + 165), "• Causal Mask (s ≤ t) bounded by Window-200.\n• Monotonic recency decay γ downweights stale drills.\nz_t = h_t + gate · AttentionOut(Q, K, V)", font=f_box_sub, fill=CLR_NAVY)

# ----------------- COLUMN 4: COGNITIVE IRT & MASTERY -----------------
b4_y = 230
round_rect((col4_x, b4_y, col4_x + col4_w, b4_y + 645), radius=10, fill=(255, 255, 255), outline=M_TEAL["border"], width=2)
draw.text((col4_x + 20, b4_y + 18), "Cognitive IRT & 6-Skill Mastery", font=f_box_title, fill=M_TEAL["header"])

# Step 4A: Cognitive Mastery Profile
b4a_y = b4_y + 55
round_rect((col4_x + 20, b4a_y, col4_x + col4_w - 20, b4a_y + 265), radius=8, fill=M_TEAL["fill"], outline=M_TEAL["border"], width=1)
draw.text((col4_x + 30, b4a_y + 12), "Interpretable Cognitive Mastery Profile:", font=f_tag, fill=M_TEAL["header"])
draw.text((col4_x + 30, b4a_y + 38), "ψ_t = σ( MLP(z_t) )  ∈ (0, 1)^6", font=f_tensor, fill=CLR_NAVY)
draw.text((col4_x + 30, b4a_y + 70), "Directly estimates student mastery across:\n[Attn, W-Mem, Logic, Lang, Crit, Meta]", font=f_box_sub, fill=CLR_MUTED)

draw.text((col4_x + 30, b4a_y + 125), "Demand-Mastery Alignment Embedding:", font=f_tag, fill=M_TEAL["header"])
draw.text((col4_x + 30, b4a_y + 150), "met = ψ_t ⊙ c_{t+1}  (mastered load)\nunmet = (1 - ψ_t) ⊙ c_{t+1}  (cognitive gap)\ne_align = Tanh(Linear([met || unmet]))", font=f_tensor, fill=CLR_NAVY)

# Step 4B: IRT Parameter Heads
b4b_y = b4_y + 340
round_rect((col4_x + 20, b4b_y, col4_x + col4_w - 20, b4b_y + 280), radius=8, fill=M_AMBER["fill"], outline=M_AMBER["border"], width=1)
draw.text((col4_x + 30, b4b_y + 12), "Multi-Component IRT Parameters:", font=f_tag, fill=M_AMBER["header"])
draw.text((col4_x + 30, b4b_y + 40), "• Student Ability (θ_t):\n  θ_t = MLP([ z_t || e_{c, t+1} || e_align ])\n• Question Difficulty (β_{t+1}):\n  β = β_que + w_d^T e_{q, t+1} + w_c^T c_{t+1}\n• Question Discrimination (α_{t+1}):\n  α = Softplus(α_que) + 0.1", font=f_box_sub, fill=CLR_NAVY)
draw.text((col4_x + 30, b4b_y + 200), "logit_IRT = α · (θ_t - β_{t+1})", font=f_tensor, fill=M_AMBER["header"])

# ----------------- COLUMN 5: OUTPUTS & LOSS -----------------
b5_y = 230
round_rect((col5_x, b5_y, col5_x + col5_w, b5_y + 645), radius=10, fill=(255, 255, 255), outline=M_EMERALD["border"], width=2)
draw.text((col5_x + 20, b5_y + 18), "Diagnostic Predictions", font=f_box_title, fill=M_EMERALD["header"])

# 5A: Final Logit Combination
b5a_y = b5_y + 55
round_rect((col5_x + 20, b5a_y, col5_x + col5_w - 20, b5a_y + 215), radius=8, fill=M_EMERALD["fill"], outline=M_EMERALD["border"], width=1)
draw.text((col5_x + 30, b5a_y + 12), "Ensemble Prediction Logit:", font=f_tag, fill=M_EMERALD["header"])
draw.text((col5_x + 30, b5a_y + 40), "logit = logit_IRT +\n        λ_aux · 0.5 (q_logit + c_logit)", font=f_tensor, fill=CLR_NAVY)
draw.text((col5_x + 30, b5a_y + 105), "P(r_{t+1}=1) = σ( logit )", font=f_title, fill=M_EMERALD["header"])
draw.text((col5_x + 30, b5a_y + 160), "AUC: 0.8119 | Acc: 82.51%", font=f_tensor, fill=CLR_NAVY)

# 5B: Explainable Radar Profile
b5b_y = b5_y + 290
round_rect((col5_x + 20, b5b_y, col5_x + col5_w - 20, b5b_y + 185), radius=8, fill=M_TEAL["fill"], outline=M_TEAL["border"], width=1)
draw.text((col5_x + 30, b5b_y + 12), "Explainable Radar Diagnostic:", font=f_tag, fill=M_TEAL["header"])
draw.text((col5_x + 30, b5b_y + 40), "Outputs 6D Radar Profile ψ_t:\n• Working Memory Load Capacity\n• Logical Reasoning Proficiency\n• Attention & Visual Readiness\n• Critical Thinking & Checking", font=f_box_sub, fill=CLR_NAVY)

# 5C: Multi-Task Loss
b5c_y = b5_y + 495
round_rect((col5_x + 20, b5c_y, col5_x + col5_w - 20, b5c_y + 130), radius=8, fill=M_ROSE["fill"], outline=M_ROSE["border"], width=1)
draw.text((col5_x + 30, b5c_y + 10), "Optimization Objective:", font=f_tag, fill=M_ROSE["header"])
draw.text((col5_x + 30, b5c_y + 35), "L = BCE( P(r_{t+1}), r_{t+1} ) +\n    λ_reg · 0.5 ( ||μ_t||^2 + ||μ_{t+1}||^2 )", font=f_tensor, fill=M_ROSE["header"])

# ----------------- CONNECTING ARROWS -----------------
# Col 1 to Col 2
draw_arrow(col1_x + col1_w, 320, col2_x, 320, color=CLR_INDIGO if 'CLR_INDIGO' in locals() else (99, 102, 241), width=4)
draw_arrow(col1_x + col1_w, 550, col2_x, 550, color=M_INDIGO["border"], width=4)

# Col 2 to Col 3
draw_arrow(col2_x + col2_w, 350, col3_x, 350, color=M_VIOLET["border"], width=4)
draw_arrow(col2_x + col2_w, 520, col3_x, 520, color=M_VIOLET["border"], width=4)

# Col 3 to Col 4
draw_arrow(col3_x + col3_w, 370, col4_x, 370, color=M_TEAL["border"], width=4)
draw_arrow(col3_x + col3_w, 540, col4_x, 540, color=M_TEAL["border"], width=4)

# Col 4 to Col 5
draw_arrow(col4_x + col4_w, 340, col5_x, 340, color=M_EMERALD["border"], width=4)
draw_arrow(col4_x + col4_w, 510, col5_x, 510, color=M_EMERALD["border"], width=4)

# Bottom Legend / Footnote
draw.line([(70, 900), (W - 70, 900)], fill=CLR_BORDER, width=2)
round_rect((70, 920, W - 70, 1010), radius=10, fill=(255, 255, 255), outline=CLR_BORDER, width=1)
draw.text((95, 935), "KEY ARCHITECTURAL HIGHLIGHTS:", font=f_sec, fill=CLR_NAVY)
draw.text((95, 970), "1. Rasch Decomposition stops question-ID memorization on small classes  |  2. 64 Cognitive Clusters group sparse concepts  |  3. 200-Step Causal Attention handles recency  |  4. Cognitive-IRT outputs interpretable 6D learner radar", font=f_box_sub, fill=CLR_MUTED)

# Crop canvas cleanly to content height (1040)
img_cropped = img.crop((0, 0, W, 1045))
img_cropped.save(str(OUT_PATH), "PNG")
print(f"Generated CAKT Architecture Diagram: {OUT_PATH} ({img_cropped.size})")
