# BrainMapper — System & UI Requirements

> **Cognitive-Aware Offline LAN Examination & Learning Analytics Platform**

## 1. Vision & Scope

**BrainMapper** combines offline Local Area Network (LAN) exam delivery (inspired by the legacy `LAN exam` / `QuizServer` reference implementation) with **Cognitive-Aware Knowledge Tracing (CA-KT)** and **explainable learner profiling**. Educators manage classes, author cognitive-tagged quizzes, forecast student scores *before* running a live exam, proctor live LAN sessions via QR code, grade objective and open-ended responses, and inspect class-level and individual 6-skill cognitive diagnostics—all with zero internet dependency during delivery.

> The reference folder `../LAN exam` remains unmodified as a coding and UX reference.

---

## 2. Core User Flows & Interfaces

### Phase 1 — Home & Cohort Foundation *(First Interface)*
1. **Home Screen (`public/index.html` / `home.html`)** — Based on Figma `BrainMapper-Home Screen (5:2)`:
   - Branded BrainMapper header emblem + gradient wordmark + subtitle (`Cognitive-aware learning analytics for offline classroom exams`).
   - **Your Classes** responsive grid displaying active class cards (`Class 1`, `Class 2`, etc.) with top accent bar, subject subtitle, student count, quiz count, and last session date.
   - **Add New Class** dashed card opening an inline/modal creation dialog (`name`, `subject`, `grade`, `accentColor`).
   - Live LAN status pill (`LAN server ready. No internet required`) backed by `GET /api/health`.
   - Quick-open trigger on each class card (or roster pill/button) to inspect the **Class Student Roster Modal**, plus clicking a class opens its **Class Dashboard**.
2. **Class Student Roster Modal** — Based on Figma `BrainMapper - Class 1 Student Roster Modal (5:93)`:
   - Search by student name or ID (`#ST-xxxx`), live count (`Showing X of Y students`).
   - Displays each student's initials avatar, name, student ID, dominant cognitive skill pill, overall mastery percentage badge, and `View` link to their profile.
   - Actions: **Add Student** modal (`POST /api/classes/:classId/students` requiring a **mandatory unique Student ID** per enrolled learner), **Export CSV** (safe CSV escaping against formula injection), and **View Full Analytics**.

### Phase 2 — Class Hub, Quiz Authoring & Pre-Quiz Score Prediction
3. **Class Dashboard** — Based on Figma `BrainMapper - Class Dashboard (6:321)`:
   - Class-scoped hub (`← All Classes`, active class badge) routing to `Quiz Library`, `Create Quizzes`, `Start Session`, and `Analyze`.
4. **Quiz Library** — Based on Figma `QuizServer - Quiz Library (7:366)`:
   - **Fix vs Figma**: Render the empty state (`No quizzes found`) and populated quiz grid *conditionally* (never stacked simultaneously), keep class-aligned subjects, and rename titles to BrainMapper.
   - Tabs (`All Quizzes`, `Templates`, `Archived`), search, category & difficulty filters, `Import CSV` (MCQ only), and `+ Create New Quiz`.
   - Every quiz card includes an inline **`Predict Scores`** CTA alongside `Edit`, `Copy` (duplicate), `Archive`, and `Delete`.
5. **Create / Edit Quiz** *(New screen addressing Figma gap)*:
   - Strictly **Multiple Choice (MCQ, Options A–D)** to guarantee standardized binary correctness (`0/1`) and cognitive vector telemetry for CA-KT / ML model training.
   - Per-question optional image upload, time limit, and explanation. Cognitive skill demand vectors (`0–3` across the 6 skills) are automatically extracted via the commercial LLM API tagging pipeline (preserving any pre-computed vector on edits).
6. **Predicted Results (Pre-Quiz Forecast — Work in Progress)** — Based on Figma `BrainMapper - Predicted Results (7:639)`:
   - Accessible from `Quiz Library` (`Predict Scores`) and `Create / Edit Quiz` (`Save & Predict Scores`), showing the `Predicted Results` title, `Work in progress` status, `Back`, and **`Start Quiz Session`** button without synthetic results.

### Phase 3 — Live Session & Student Exam Delivery
7. **Start Session / Live Monitor** *(New screen addressing Figma gap)*:
   - LAN IPv4 selector + QR code (`/api/qrcode`) + shareable `http://<lan-ip>:<port>/exam` URL.
   - Quiz selector (or pre-selected quiz from `Predicted Results` / `Quiz Library`).
   - Live connected participant list, submission status tracking, and `Start Session` / `End Session` controls synced to server state (`currentSession.json`).
8. **Student Exam Portal (`/exam`)** — Adapted from `LAN exam/public/index.html`:
   - **Assigned Student ID Join**: Students enter their assigned unique **Student ID** (instead of typing a display name); the server verifies enrollment against the active class roster and binds their name & profile automatically.
   - Reload-safe student identity & session recovery (does **not** wipe `participantId` on page reload).
   - Security fix: `/api/currentQuiz` **strips `correct` and `explanation`** from student payloads.
   - Sequential/active per-question timer fix (only active question's timer counts down, rather than all starting simultaneously), draft auto-save, flagging, dark mode, font scale, and TTS.

### Phase 4 — Analytics, Grading & Explainable Cognitive Profiles
9. **Analyze Hub** — Based on Figma `BrainMapper - Analyze (8:1240)`:
   - Unified persistent top navigation bar (`Dashboard | Analyze | Library | Monitor | Settings`) across class workspace views.
   - Class KPIs (`Quizzes Completed`, `Class Average`, `Students`), `Quiz Grades` & `Student Profiles` entry cards, and `Cognitive Diagnostic Pulse` summary + export.
10. **Quiz Grades & Question Review** — Based on Figma `BrainMapper-Quiz Grades-2 (9:2490)`:
    - Session selector sidebar, KPI cards (`Participants`, `Average`, `Highest`, `Completion`), score distribution bar chart, per-student MCQ response inspection & score override modal, Leaderboard table, and `Export CSV / PDF / HTML`.
11. **Overall Cognitive Skills** — Based on Figma `BrainMapper - Overall Cognitive Skills (9:2865)`:
    - **Fixes vs Figma (`9:2865`)**:
      - `Strongest Domain` and `Needs Attention` highlight cards use proper flex constraints (`min-width: 0`) so `"Logical Reasoning"` and `"Working Memory"` never clip.
      - Class 6-axis hexagonal radar SVG includes generous padding/viewBox margins and two-line axis labels with centered bottom alignment so labels never touch card borders or rings.
    - Class radar vs `80%` benchmark, ranked 6-skill progress bars, searchable/filterable/paginated student list with mini radar icons.
12. **Student Profile** — Based on Figma `BrainMapper - Student Profile (9:3233)`:
    - Student summary + `Overall Cognitive Score`, 6-axis radar (`Student` vs `Class Average`), `Individual Competencies` (`≥75%` benchmark), `Strengths` & `Areas to Improve`, `Why this profile?` KT explanation, longitudinal `Knowledge Progress` chart, and `Recent Quizzes` table.
    - Consistent student telemetry across Roster, Predicted Results, Overall Cognitive Skills, and Student Profile.

---

## 3. Cognitive Skill Taxonomy

| Skill | Scale | Description |
|---|---|---|
| **Attention** | Demand `0–3` / Mastery `0–100` | Selective focus on key elements, diagram parsing, filtering distractors |
| **Working Memory** | Demand `0–3` / Mastery `0–100` | Retaining and manipulating intermediate steps and multi-clause constraints |
| **Logical Reasoning** | Demand `0–3` / Mastery `0–100` | Deductive/inductive reasoning, patterns, proofs, and rules |
| **Language Processing** | Demand `0–3` / Mastery `0–100` | Decoding domain phrasing, multi-clause text, and linguistic nuance |
| **Critical Thinking** | Demand `0–3` / Mastery `0–100` | Evaluating alternatives, checking boundary cases, and counterexamples |
| **Metacognition** | Demand `0–3` / Mastery `0–100` | Strategy planning, self-monitoring, and solution verification |

---

## 4. Technical & Security Requirements (Fixes Over `LAN exam`)

1. **No Answer Key Leakage**: Student endpoints (`/api/currentQuiz`) MUST omit `correct` and `explanation` fields until post-submission or host review.
2. **Safe Identifiers**: All `classId`, `studentId`, `quizId`, and `sessionId` values MUST be validated against `/^[A-Za-z0-9_-]{1,200}$/`. Session IDs MUST sanitize quiz names cleanly so duplicated quizzes (e.g. `... (Copy)`) never trigger `400 Invalid session ID`.
3. **Question Pool Grading Accuracy**: When `useQuestionPool` serves a subset (`poolSize`), grading MUST score strictly against the `questionMapping` served to that student (`totalGradeable` reflects asked gradeable questions, not unasked pool items).
4. **Atomic Persistence**: All JSON writes (`classes`, `students`, `quizzes`, `sessions`, `runtimeState`) use temp-file + rename (`writeJson`) and corrupt-file tolerance (`readJson`).
5. **Offline Self-Sufficiency**: All fonts (`Inter`), icons (local SVG assets), charts (canvas/SVG), and vendor assets are bundled locally—zero external CDN requests.
6. **LAN Access Separation**: Educator routes/views (`admin` / `class` / `analytics` / `create` / `grading`) are separated from the student exam entry (`/exam`) and protected by localhost-first checks or optional session PIN on LAN.
