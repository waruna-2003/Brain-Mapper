"""
Isolated Local Bridge Server for Google Gemini Web Browser Extension Annotation.

Targeted for cross-validation on 500 purely text-based questions against DeepSeek.
Coordinates question serving, schema validation, and atomic disk writes on port 8767.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

# Paths relative to this script
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parents[1]
DATA_DIR = BASE_DIR / "data"
QUESTIONS_CSV = PROJECT_ROOT / "data" / "processed" / "xes3g5m" / "questions.csv"
ANNOTATIONS_FILE = DATA_DIR / "gemini_annotations.jsonl"
FAILURES_FILE = DATA_DIR / "gemini_failures.jsonl"
STATE_FILE = DATA_DIR / "state.json"
DEEPSEEK_ANNOTATIONS_FILE = PROJECT_ROOT / "tools" / "deepseek_extension" / "data" / "deepseek_annotations.jsonl"

REQUIRED_SKILLS = [
    "attention",
    "working_memory",
    "logical_reasoning",
    "language_processing",
    "critical_thinking",
    "metacognition",
]

DEFAULT_TARGET_COUNT = 500

PROMPT_TEMPLATE = """You are annotating the cognitive requirements of an educational mathematics question for a cognitive-aware knowledge-tracing research dataset.

Evaluate what a typical Grade 3 student must do to solve the question. Do not judge how difficult the wording feels to an adult. Do not infer requirements from a correct answer, knowledge-component label, student response, or other information that is not included below.

Use this scale for every skill:
0 = not required or negligible
1 = low: one simple, direct use
2 = moderate: sustained or multi-step use
3 = high: central, complex, or sustained use

Skill definitions:
- attention: Select and maintain focus on relevant details, constraints, symbols, options, or numbers while ignoring distractions.
- working_memory: Hold and manipulate multiple pieces of information or intermediate calculation results. Simple recall alone is not working memory.
- logical_reasoning: Apply rules, relations, deductions, sequencing, or multi-step mathematical reasoning to reach a conclusion.
- language_processing: Understand vocabulary, grammar, references, or a linguistically complex problem statement. Reading one short direct sentence is at most low.
- critical_thinking: Compare plausible approaches, evaluate evidence or assumptions, detect ambiguity, or select and justify a strategy. Routine application of a known procedure is not automatically critical thinking.
- metacognition: Explicitly plan, monitor, check, or reflect on one's own approach. Most routine questions should receive 0 unless self-monitoring is genuinely required by the task.

Score requirements independently. Use the full 0-3 range, but do not inflate scores simply because the question is mathematical. Confidence is confidence in the annotation (0.0-1.0), not confidence that a student answers correctly. Give one concise rationale grounded only in the supplied question.

Question ID: {question_id}
Question:
{question_text}

Options:
{options_formatted}

CRITICAL: Return ONLY a single valid JSON object. Do not include markdown code blocks, preamble, or commentary. The response must parse directly into this structure:
{{
  "question_id": {question_id},
  "attention": <integer 0-3>,
  "working_memory": <integer 0-3>,
  "logical_reasoning": <integer 0-3>,
  "language_processing": <integer 0-3>,
  "critical_thinking": <integer 0-3>,
  "metacognition": <integer 0-3>,
  "confidence": <float 0.0-1.0>,
  "short_rationale": "<concise explanation>"
}}"""


class GeminiAnnotationManager:
    """Manages 500 text-based questions cross-validation queue and atomic writes."""

    def __init__(
        self,
        questions_path: Path = QUESTIONS_CSV,
        target_count: int = DEFAULT_TARGET_COUNT,
        text_only: bool = True,
    ) -> None:
        self.questions_path = questions_path
        self.target_count = target_count
        self.text_only = text_only

        self.all_questions: list[dict[str, Any]] = []
        self.target_questions: list[dict[str, Any]] = []
        self.questions_by_id: dict[int, dict[str, Any]] = {}
        self.completed_ids: set[int] = set()
        self.failed_ids: set[int] = set()
        self.skipped_ids: set[int] = set()
        self.failure_counts: dict[int, int] = {}
        self.deepseek_annotations: dict[int, dict[str, Any]] = {}

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.load_deepseek_reference()
        self.load_questions()
        self.load_completed()
        self.load_failures()

    def load_deepseek_reference(self) -> None:
        self.deepseek_annotations.clear()
        if not DEEPSEEK_ANNOTATIONS_FILE.exists():
            return

        with DEEPSEEK_ANNOTATIONS_FILE.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    self.deepseek_annotations[int(rec["question_id"])] = rec
                except Exception:
                    continue

    def load_questions(self) -> None:
        if not self.questions_path.exists():
            raise FileNotFoundError(f"Questions CSV not found at: {self.questions_path}")

        self.all_questions.clear()
        self.target_questions.clear()
        self.questions_by_id.clear()

        with self.questions_path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                q_id = int(row["question_id"])
                options = json.loads(row["options_json"]) if row.get("options_json") else []
                image_paths = json.loads(row["image_paths_json"]) if row.get("image_paths_json") else []
                has_images = (
                    len(image_paths) > 0
                    or row.get("requires_image", "") in ("1", "True", "true")
                    or row.get("has_images", "").lower() == "true"
                )
                record = {
                    "question_id": q_id,
                    "question_text": row.get("question_text", ""),
                    "options": options,
                    "image_paths": image_paths,
                    "has_images": has_images,
                }
                self.all_questions.append(record)
                self.questions_by_id[q_id] = record

        # Filter strictly for text-only questions (no diagrams/images)
        text_only_pool = [q for q in self.all_questions if not q["has_images"] and len(q["image_paths"]) == 0]

        # Prioritize questions that DeepSeek has already annotated to maximize 1:1 cross-validation overlap
        in_ds = [q for q in text_only_pool if q["question_id"] in self.deepseek_annotations]
        not_in_ds = [q for q in text_only_pool if q["question_id"] not in self.deepseek_annotations]

        in_ds.sort(key=lambda x: x["question_id"])
        not_in_ds.sort(key=lambda x: x["question_id"])

        ordered_pool = in_ds + not_in_ds
        self.target_questions = ordered_pool[: self.target_count]
        self.target_questions.sort(key=lambda x: x["question_id"])

    def load_completed(self) -> None:
        self.completed_ids.clear()
        if not ANNOTATIONS_FILE.exists():
            return

        with ANNOTATIONS_FILE.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    self.completed_ids.add(int(record["question_id"]))
                except Exception:
                    continue

    def load_failures(self) -> None:
        self.failed_ids.clear()
        if not FAILURES_FILE.exists():
            return

        with FAILURES_FILE.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    q_id = int(record["question_id"])
                    self.failure_counts[q_id] = self.failure_counts.get(q_id, 0) + 1
                    if self.failure_counts[q_id] >= 3:
                        self.failed_ids.add(q_id)
                except Exception:
                    continue

    def get_next_question(self) -> dict[str, Any] | None:
        for q in self.target_questions:
            q_id = q["question_id"]
            if q_id in self.completed_ids:
                continue
            if q_id in self.failed_ids:
                continue
            if q_id in self.skipped_ids:
                continue
            return q
        return None

    def build_prompt(self, question: dict[str, Any]) -> str:
        q_id = question["question_id"]
        q_text = question["question_text"]
        options = question.get("options", [])
        if options:
            options_fmt = "\n".join(f"- {opt}" for opt in options)
        else:
            options_fmt = "No explicit multiple-choice options provided."

        return PROMPT_TEMPLATE.format(
            question_id=q_id,
            question_text=q_text,
            options_formatted=options_fmt,
        )

    def record_success(
        self,
        question_id: int,
        scores: dict[str, int],
        confidence: float,
        short_rationale: str,
        raw_response: str = "",
    ) -> None:
        for skill in REQUIRED_SKILLS:
            if skill not in scores:
                raise ValueError(f"Missing required cognitive skill: {skill}")
            val = scores[skill]
            if not isinstance(val, int) or val < 0 or val > 3:
                raise ValueError(f"Score for {skill} must be integer 0-3, got {val}")

        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {confidence}")

        record = {
            "question_id": question_id,
            "attention": scores["attention"],
            "working_memory": scores["working_memory"],
            "logical_reasoning": scores["logical_reasoning"],
            "language_processing": scores["language_processing"],
            "critical_thinking": scores["critical_thinking"],
            "metacognition": scores["metacognition"],
            "confidence": round(float(confidence), 3),
            "short_rationale": short_rationale.strip(),
            "annotated_at": datetime.now(UTC).isoformat(),
            "annotator_model": "gemini-pro-web-cross-val",
            "is_text_only": True,
            "raw_response": raw_response,
        }

        with ANNOTATIONS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        self.completed_ids.add(question_id)
        if question_id in self.failure_counts:
            del self.failure_counts[question_id]
        self._save_state()

    def record_failure(self, question_id: int, error_msg: str) -> None:
        self.failure_counts[question_id] = self.failure_counts.get(question_id, 0) + 1
        record = {
            "question_id": question_id,
            "error": error_msg,
            "attempt": self.failure_counts[question_id],
            "failed_at": datetime.now(UTC).isoformat(),
        }
        with FAILURES_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        if self.failure_counts[question_id] >= 3:
            self.failed_ids.add(question_id)
        self._save_state()

    def skip_question(self, question_id: int) -> None:
        self.skipped_ids.add(question_id)
        self._save_state()

    def _save_state(self) -> None:
        target_ids = set(q["question_id"] for q in self.target_questions)
        completed_in_target = len(self.completed_ids.intersection(target_ids))
        state = {
            "target_count": len(self.target_questions),
            "completed_count": completed_in_target,
            "failed_count": len(self.failed_ids),
            "skipped_count": len(self.skipped_ids),
            "completed_ids": sorted(list(self.completed_ids.intersection(target_ids))),
            "last_updated": datetime.now(UTC).isoformat(),
        }
        try:
            temp_file = DATA_DIR / "state.tmp"
            with temp_file.open("w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            temp_file.replace(STATE_FILE)
        except OSError:
            try:
                with STATE_FILE.open("w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2)
            except Exception as e:
                print(f"[Gemini Bridge] Warning: could not write state.json: {e}", file=sys.stderr)

    def get_stats(self) -> dict[str, Any]:
        target_ids = set(q["question_id"] for q in self.target_questions)
        completed_in_target = self.completed_ids.intersection(target_ids)
        total_target = len(self.target_questions)
        completed_count = len(completed_in_target)
        failed_count = len(self.failed_ids)
        remaining_count = max(0, total_target - completed_count - failed_count)
        pct = (completed_count / total_target * 100.0) if total_target > 0 else 0.0

        ds_overlap = len(completed_in_target.intersection(self.deepseek_annotations.keys()))

        return {
            "target_total": total_target,
            "completed": completed_count,
            "remaining": remaining_count,
            "failed": failed_count,
            "percent": round(pct, 1),
            "deepseek_overlap_count": ds_overlap,
            "text_only": True,
        }

    def get_cross_validation_comparison(self) -> dict[str, Any]:
        target_ids = set(q["question_id"] for q in self.target_questions)
        overlap_ids = sorted(list(self.completed_ids.intersection(target_ids).intersection(self.deepseek_annotations.keys())))

        if not overlap_ids:
            return {
                "overlap_count": 0,
                "message": "No overlapping text-based annotations completed yet.",
                "skills": {},
            }

        gemini_records: dict[int, dict[str, Any]] = {}
        if ANNOTATIONS_FILE.exists():
            with ANNOTATIONS_FILE.open(encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    q_id = int(rec["question_id"])
                    if q_id in overlap_ids:
                        gemini_records[q_id] = rec

        skill_diffs: dict[str, dict[str, float]] = {}
        for skill in REQUIRED_SKILLS:
            gem_vals = [float(gemini_records[qid][skill]) for qid in overlap_ids if qid in gemini_records]
            ds_vals = [float(self.deepseek_annotations[qid][skill]) for qid in overlap_ids if qid in gemini_records]

            if not gem_vals:
                continue

            gem_mean = sum(gem_vals) / len(gem_vals)
            ds_mean = sum(ds_vals) / len(ds_vals)
            mae = sum(abs(g - d) for g, d in zip(gem_vals, ds_vals)) / len(gem_vals)
            exact_match_pct = (sum(1 for g, d in zip(gem_vals, ds_vals) if g == d) / len(gem_vals)) * 100.0

            skill_diffs[skill] = {
                "gemini_mean": round(gem_mean, 2),
                "deepseek_mean": round(ds_mean, 2),
                "mae": round(mae, 2),
                "exact_match_percent": round(exact_match_pct, 1),
            }

        return {
            "overlap_count": len(overlap_ids),
            "skills": skill_diffs,
        }


# Global Manager
MANAGER = GeminiAnnotationManager()


class GeminiBridgeHandler(BaseHTTPRequestHandler):
    """HTTP handler supporting JSON APIs for Gemini Web Extension."""

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            self.send_response(HTTPStatus.OK)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "status": "ok",
                        "service": "gemini_extension_bridge",
                        "port": 8767,
                        "text_only": True,
                        "target_count": MANAGER.target_count,
                    }
                ).encode("utf-8")
            )
            return

        if path == "/api/next_question":
            next_q = MANAGER.get_next_question()
            self.send_response(HTTPStatus.OK)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            if next_q is None:
                stats = MANAGER.get_stats()
                resp = {"done": True, "message": "All 500 text-only questions completed!", "stats": stats}
            else:
                prompt = MANAGER.build_prompt(next_q)
                stats = MANAGER.get_stats()
                resp = {
                    "done": False,
                    "question_id": next_q["question_id"],
                    "prompt": prompt,
                    "has_images": False,  # Strictly text-based
                    "target_total": stats["target_total"],
                    "completed_count": stats["completed"],
                }

            self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        if path == "/api/stats":
            stats = MANAGER.get_stats()
            self.send_response(HTTPStatus.OK)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(stats).encode("utf-8"))
            return

        if path == "/api/cross_validation":
            cv_data = MANAGER.get_cross_validation_comparison()
            self.send_response(HTTPStatus.OK)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(cv_data).encode("utf-8"))
            return

        self.send_error(HTTPStatus.NOT_FOUND, f"Endpoint {path} not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length)

        try:
            body = json.loads(post_body.decode("utf-8")) if post_body else {}
        except Exception as e:
            self.send_error(HTTPStatus.BAD_REQUEST, f"Malformed JSON: {e}")
            return

        if path == "/api/submit":
            try:
                q_id = int(body["question_id"])
                scores = body["scores"]
                confidence = float(body.get("confidence", 0.95))
                short_rationale = str(body.get("short_rationale", ""))
                raw_resp = str(body.get("raw_response", ""))

                MANAGER.record_success(
                    question_id=q_id,
                    scores=scores,
                    confidence=confidence,
                    short_rationale=short_rationale,
                    raw_response=raw_resp,
                )

                self.send_response(HTTPStatus.OK)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"status": "saved", "question_id": q_id, "stats": MANAGER.get_stats()}).encode("utf-8")
                )
            except Exception as err:
                self.send_response(HTTPStatus.BAD_REQUEST)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(err)}).encode("utf-8"))
            return

        if path == "/api/fail":
            q_id = int(body.get("question_id", -1))
            err_msg = str(body.get("error", "Unknown error"))
            if q_id >= 0:
                MANAGER.record_failure(q_id, err_msg)
            self.send_response(HTTPStatus.OK)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "recorded_failure", "question_id": q_id}).encode("utf-8"))
            return

        if path == "/api/skip":
            q_id = int(body.get("question_id", -1))
            if q_id >= 0:
                MANAGER.skip_question(q_id)
            self.send_response(HTTPStatus.OK)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "skipped", "question_id": q_id}).encode("utf-8"))
            return

        self.send_error(HTTPStatus.NOT_FOUND, f"Endpoint {path} not found")

    def log_message(self, format: str, *args: Any) -> None:
        sys.stdout.write(f"[Gemini Bridge] {self.address_string()} - {format % args}\n")
        sys.stdout.flush()


def run_server(host: str = "127.0.0.1", port: int = 8767) -> None:
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, GeminiBridgeHandler)
    stats = MANAGER.get_stats()
    print("=" * 65)
    print("  BRAIN MAPPER: GEMINI WEB CROSS-VALIDATION BRIDGE SERVER")
    print("  (STRICTLY FILTERED FOR 500 TEXT-BASED QUESTIONS)")
    print("=" * 65)
    print(f"  Target Text Questions: {stats['target_total']} (100% Text-Only)")
    print(f"  Already Completed    : {stats['completed']}")
    print(f"  Remaining            : {stats['remaining']}")
    print(f"  DeepSeek Overlap     : {stats['deepseek_overlap_count']}")
    print(f"  Server Listening on  : http://{host}:{port}")
    print(f"  Chrome Extension     : Load 'tools/gemini_extension/extension'")
    print("=" * 65)
    print("Press Ctrl+C to stop server.\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Gemini Bridge] Shutting down gracefully...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
