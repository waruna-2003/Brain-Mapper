"""
CLI Progress Checker for Gemini Web Cross-Validation Annotations.
"""

from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
ANNOTATIONS_FILE = DATA_DIR / "gemini_annotations.jsonl"
FAILURES_FILE = DATA_DIR / "gemini_failures.jsonl"
STATE_FILE = DATA_DIR / "state.json"
DEEPSEEK_FILE = BASE_DIR.parents[0] / "deepseek_extension" / "data" / "deepseek_annotations.jsonl"

TARGET_COUNT = 500


def check_progress():
    print("=" * 60)
    print("  BRAIN MAPPER: GEMINI WEB TEXT-ONLY ANNOTATION PROGRESS")
    print("=" * 60)

    completed_ids = set()
    records = []
    if ANNOTATIONS_FILE.exists():
        with ANNOTATIONS_FILE.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    q_id = int(rec["question_id"])
                    completed_ids.add(q_id)
                    records.append(rec)
                except Exception:
                    pass

    failures = []
    if FAILURES_FILE.exists():
        with FAILURES_FILE.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        failures.append(json.loads(line))
                    except Exception:
                        pass

    ds_ids = set()
    if DEEPSEEK_FILE.exists():
        with DEEPSEEK_FILE.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        ds_ids.add(int(json.loads(line)["question_id"]))
                    except Exception:
                        pass

    overlap = completed_ids.intersection(ds_ids)
    pct = (len(completed_ids) / TARGET_COUNT) * 100.0 if TARGET_COUNT > 0 else 0.0

    print(f"Target Sample (Text-Only) : {TARGET_COUNT} questions")
    print(f"Completed by Gemini       : {len(completed_ids)} / {TARGET_COUNT} ({pct:.1f}%)")
    print(f"Remaining Questions       : {max(0, TARGET_COUNT - len(completed_ids))}")
    print(f"Logged Failures           : {len(failures)}")
    print(f"DeepSeek Overlap (Ready)  : {len(overlap)} questions")
    print("-" * 60)

    if records:
        skills = [
            "attention",
            "working_memory",
            "logical_reasoning",
            "language_processing",
            "critical_thinking",
            "metacognition",
        ]
        print("Gemini Cognitive Score Distribution (Current Sample):")
        for s in skills:
            vals = [float(r[s]) for r in records if s in r]
            if vals:
                mean_v = sum(vals) / len(vals)
                print(f"  • {s:<20}: {mean_v:.2f} / 3.0")

    print("=" * 60)


if __name__ == "__main__":
    check_progress()
