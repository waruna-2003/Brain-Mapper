"""
Export the 500 text-only questions subset to CSV for Gemini annotation.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE_DIR.parents[1]
QUESTIONS_CSV = PROJECT_ROOT / "data" / "processed" / "xes3g5m" / "questions.csv"
DEEPSEEK_FILE = PROJECT_ROOT / "tools" / "deepseek_extension" / "data" / "deepseek_annotations.jsonl"
OUT_CSV = BASE_DIR / "data" / "text_only_500_questions.csv"

TARGET_COUNT = 500


def export_sample():
    if not QUESTIONS_CSV.exists():
        print(f"Error: {QUESTIONS_CSV} does not exist.")
        return

    ds_completed_ids = set()
    if DEEPSEEK_FILE.exists():
        with DEEPSEEK_FILE.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        ds_completed_ids.add(int(json.loads(line)["question_id"]))
                    except Exception:
                        pass

    text_only_questions = []
    with QUESTIONS_CSV.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            q_id = int(row["question_id"])
            image_paths = json.loads(row.get("image_paths_json") or "[]")
            requires_img = row.get("requires_image", "").lower() in ("1", "true")
            has_imgs = row.get("has_images", "").lower() == "true" or len(image_paths) > 0 or requires_img
            if not has_imgs:
                text_only_questions.append(row)

    # Prioritize questions already annotated by DeepSeek for 1:1 cross-validation
    in_ds = [q for q in text_only_questions if int(q["question_id"]) in ds_completed_ids]
    not_in_ds = [q for q in text_only_questions if int(q["question_id"]) not in ds_completed_ids]

    in_ds.sort(key=lambda x: int(x["question_id"]))
    not_in_ds.sort(key=lambda x: int(x["question_id"]))

    selected = (in_ds + not_in_ds)[:TARGET_COUNT]
    selected.sort(key=lambda x: int(x["question_id"]))

    fieldnames = list(selected[0].keys()) if selected else []
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected)

    overlap_count = sum(1 for q in selected if int(q["question_id"]) in ds_completed_ids)

    print(f"Successfully exported {len(selected)} text-only questions to:")
    print(f"  -> {OUT_CSV}")
    print(f"  • Total text questions exported : {len(selected)}")
    print(f"  • Overlap in DeepSeek corpus   : {overlap_count} / {len(selected)} (100% text-based)")


if __name__ == "__main__":
    export_sample()
