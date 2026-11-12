# Brain Mapper: Google Gemini Web Text-Only Extension Subsystem

> **Purpose**: Automated browser bridge to annotate a balanced **500 text-based question sample** on **Google Gemini Web** (`gemini.google.com`) for direct **inter-model cross-validation** against DeepSeek-R1.

---

## Architecture Overview

```
tools/gemini_extension/
├── bridge_server.py               # Local HTTP daemon on port 8767 (strictly filters text-only questions)
├── config.yaml                    # Configuration (Target: 500 questions, text_only: true, Port: 8767)
├── README.md                      # Complete setup and operator guide
├── data/
│   ├── gemini_annotations.jsonl   # Atomic output records from Gemini Web
│   ├── gemini_failures.jsonl      # Failed question attempts & error logs
│   ├── text_only_500_questions.csv# Exported 500 text-only questions (100% diagram-free)
│   └── state.json                 # Real-time state persistence
├── extension/                     # Chrome Manifest V3 Extension
│   ├── manifest.json              # Matches gemini.google.com, Port 8767
│   ├── content/
│   │   ├── gemini_dom.js          # Gemini DOM adapter (.ql-editor, Quill/Angular events, send button)
│   │   ├── parser.js              # Extracts JSON, validates 6 skills (0-3), anti-stale protection
│   │   └── content.js             # Automation loop connecting Gemini tab to bridge
│   └── popup/
│       ├── popup.html             # UI with 500 text-Q progress bar, status pills, delay slider
│       ├── popup.js               # Popup controller with automated F5 reload detection
│       └── popup.css              # Dark theme with Google Gemini gradient accents
├── scripts/
│   ├── check_progress.py          # CLI progress and score summary viewer
│   ├── export_text_only_sample.py # Exports 500 text-only sample questions
│   └── compare_deepseek_vs_gemini.py # Statistical cross-validation (MAE, Pearson r, Cohen's Kappa)
└── tests/
    ├── test_gemini_bridge_server.py # 4 unit tests for text filtering & queue
    └── test_gemini_parser.py        # 3 unit tests for parser & anti-stale guards
```

---

## Key Highlights

1. **Strictly Text-Based Questions**:
   - Automatically excludes all geometry diagrams and image-dependent questions.
   - All 500 selected questions are 100% text problems.
   - All 500 already have matching completed DeepSeek-R1 annotations for direct 1:1 cross-validation.
2. **Dedicated Port `8767`**:
   - Operates independently on port `8767`, avoiding conflicts with DeepSeek (`8765`) or any other server.
3. **Gemini Web Quill / Rich-Text Adapter**:
   - Custom-engineered DOM adapter supporting Gemini's `.ql-editor` / `rich-textarea` and Angular event bus.
   - Automatically handles prompt insertion and triggers Gemini's Send button.
   - Accurately tracks Gemini's `<model-response>` elements while strictly ignoring `<user-query>`.
4. **Statistical Cross-Validation**:
   - `compare_deepseek_vs_gemini.py` calculates Mean Absolute Error (MAE), Pearson correlation ($r$), Exact Agreement %, and weighted Cohen's Kappa ($\kappa_w$).

---

## Quick Start Guide

### Step 1: Start the Gemini Bridge Server
In your terminal, run:

```powershell
.venv\Scripts\python.exe tools/gemini_extension/bridge_server.py
```

Console output:
```
=================================================================
  BRAIN MAPPER: GEMINI WEB CROSS-VALIDATION BRIDGE SERVER
  (STRICTLY FILTERED FOR 500 TEXT-BASED QUESTIONS)
=================================================================
  Target Text Questions: 500 (100% Text-Only)
  Already Completed    : 0
  Remaining            : 500
  DeepSeek Overlap     : 0
  Server Listening on  : http://127.0.0.1:8767
  Chrome Extension     : Load 'tools/gemini_extension/extension'
=================================================================
```

---

### Step 2: Load Extension in Chrome
1. In Google Chrome, go to `chrome://extensions/`.
2. Enable **Developer mode** (toggle in upper right).
3. Click **Load unpacked** and select:
   `D:\Brain Mapper\tools\gemini_extension\extension`
4. Pin the **Brain Mapper Gemini** extension to your toolbar.

---

### Step 3: Open Gemini and Run Annotation
1. Open a Chrome tab to [https://gemini.google.com](https://gemini.google.com) (make sure you are signed into your Google account).
2. Click the extension icon in your toolbar.
3. Check the status pills:
   - **Bridge Server (8767)**: `Online` (green)
   - **Gemini Tab**: `Connected` (green)
   *(If it displays "Press F5", reload the Gemini tab once so the content script attaches).*
4. Click **Start Automation**.

---

### Step 4: Monitor & Cross-Validate

- **Check Live Progress**:
  ```powershell
  .venv\Scripts\python.exe tools/gemini_extension/scripts/check_progress.py
  ```

- **Run Cross-Validation Report (DeepSeek vs. Gemini)**:
  ```powershell
  .venv\Scripts\python.exe tools/gemini_extension/scripts/compare_deepseek_vs_gemini.py
  ```
  Exports reports to `data/cross_validation_gemini_report.json` and `.csv`.
