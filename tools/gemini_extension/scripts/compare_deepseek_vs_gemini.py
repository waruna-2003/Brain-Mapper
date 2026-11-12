"""
Comprehensive Statistical Cross-Validation: DeepSeek-R1 vs. Google Gemini Web.

Computes Inter-Rater Reliability, Pearson Correlation, Mean Absolute Error (MAE),
and Exact / Within-1 Agreement across the 6-skill cognitive rubric on text-based questions.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE_DIR.parents[1]
GEMINI_FILE = BASE_DIR / "data" / "gemini_annotations.jsonl"
DEEPSEEK_FILE = PROJECT_ROOT / "tools" / "deepseek_extension" / "data" / "deepseek_annotations.jsonl"
OUT_REPORT_JSON = BASE_DIR / "data" / "cross_validation_gemini_report.json"
OUT_REPORT_CSV = BASE_DIR / "data" / "cross_validation_gemini_report.csv"

SKILLS = [
    "attention",
    "working_memory",
    "logical_reasoning",
    "language_processing",
    "critical_thinking",
    "metacognition",
]


def mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def std_dev(vals: list[float], m: float) -> float:
    if len(vals) < 2:
        return 0.0
    return math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1))


def pearson_r(x: list[float], y: list[float]) -> float:
    if len(x) != len(y) or len(x) < 2:
        return 0.0
    mx = mean(x)
    my = mean(y)
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    den = math.sqrt(sum((xi - mx) ** 2 for xi in x) * sum((yi - my) ** 2 for yi in y))
    return num / den if den != 0.0 else 0.0


def cohens_kappa(x: list[int], y: list[int], num_classes: int = 4) -> float:
    """Computes quadratic weighted Cohen's Kappa for 0-3 ordinal scales."""
    if len(x) != len(y) or len(x) == 0:
        return 0.0

    n = len(x)
    matrix = [[0] * num_classes for _ in range(num_classes)]
    for xi, yi in zip(x, y):
        if 0 <= xi < num_classes and 0 <= yi < num_classes:
            matrix[xi][yi] += 1

    max_diff_sq = (num_classes - 1) ** 2
    row_sums = [sum(matrix[i][j] for j in range(num_classes)) for i in range(num_classes)]
    col_sums = [sum(matrix[i][j] for i in range(num_classes)) for j in range(num_classes)]

    observed_agreement = 0.0
    expected_agreement = 0.0

    for i in range(num_classes):
        for j in range(num_classes):
            weight = 1.0 - ((i - j) ** 2) / max_diff_sq
            observed_agreement += weight * (matrix[i][j] / n)
            expected_agreement += weight * ((row_sums[i] / n) * (col_sums[j] / n))

    if expected_agreement == 1.0:
        return 1.0

    return (observed_agreement - expected_agreement) / (1.0 - expected_agreement)


def run_cross_validation():
    print("=" * 75)
    print("  BRAIN MAPPER: TEXT-BASED CROSS-VALIDATION ANALYSIS")
    print("  Comparing: DeepSeek-R1 (Primary) vs. Google Gemini Web (Cross-Validation)")
    print("=" * 75)

    if not GEMINI_FILE.exists():
        print(f"Error: Gemini annotations file not found at {GEMINI_FILE}")
        print("Please annotate questions via the Gemini extension first.")
        return

    if not DEEPSEEK_FILE.exists():
        print(f"Error: DeepSeek annotations file not found at {DEEPSEEK_FILE}")
        return

    gem_records: dict[int, dict[str, Any]] = {}
    with GEMINI_FILE.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    r = json.loads(line)
                    gem_records[int(r["question_id"])] = r
                except Exception:
                    pass

    ds_records: dict[int, dict[str, Any]] = {}
    with DEEPSEEK_FILE.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    r = json.loads(line)
                    ds_records[int(r["question_id"])] = r
                except Exception:
                    pass

    overlap_ids = sorted(list(set(gem_records.keys()).intersection(ds_records.keys())))
    n_overlap = len(overlap_ids)

    print(f"Gemini Completed Annotations  : {len(gem_records)}")
    print(f"DeepSeek Completed Annotations: {len(ds_records)}")
    print(f"Paired Text Questions (N)     : {n_overlap}")
    print("-" * 75)

    if n_overlap == 0:
        print("No overlapping questions found between Gemini and DeepSeek yet.")
        return

    results = []
    print(
        f"{'Skill Name':<21} | {'DeepSeek':<9} | {'Gemini':<9} | {'MAE':<6} | {'Exact%':<7} | {'±1%':<6} | {'Pearson r':<9} | {'Kappa'}"
    )
    print("-" * 75)

    for skill in SKILLS:
        ds_vals = [float(ds_records[qid][skill]) for qid in overlap_ids]
        gem_vals = [float(gem_records[qid][skill]) for qid in overlap_ids]
        ds_ints = [int(round(v)) for v in ds_vals]
        gem_ints = [int(round(v)) for v in gem_vals]

        ds_m = mean(ds_vals)
        gem_m = mean(gem_vals)
        mae = mean([abs(d - g) for d, g in zip(ds_vals, gem_vals)])
        exact_pct = (sum(1 for d, g in zip(ds_ints, gem_ints) if d == g) / n_overlap) * 100.0
        within1_pct = (sum(1 for d, g in zip(ds_ints, gem_ints) if abs(d - g) <= 1) / n_overlap) * 100.0
        r_val = pearson_r(ds_vals, gem_vals)
        kappa = cohens_kappa(ds_ints, gem_ints)

        results.append(
            {
                "skill": skill,
                "n": n_overlap,
                "deepseek_mean": round(ds_m, 2),
                "gemini_mean": round(gem_m, 2),
                "mae": round(mae, 2),
                "exact_agreement_percent": round(exact_pct, 1),
                "within_1_percent": round(within1_pct, 1),
                "pearson_r": round(r_val, 3),
                "weighted_kappa": round(kappa, 3),
            }
        )

        print(
            f"{skill:<21} | {ds_m:<9.2f} | {gem_m:<9.2f} | {mae:<6.2f} | {exact_pct:<6.1f}% | {within1_pct:<5.1f}% | {r_val:<9.3f} | {kappa:.3f}"
        )

    print("=" * 75)

    OUT_REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_REPORT_JSON.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "sample_size": n_overlap,
                "dataset_type": "text_only",
                "evaluated_at": str(Path(__file__).name),
                "skills": results,
            },
            f,
            indent=2,
        )

    with OUT_REPORT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    print(f"Reports saved to:")
    print(f"  • JSON: {OUT_REPORT_JSON}")
    print(f"  • CSV : {OUT_REPORT_CSV}")


if __name__ == "__main__":
    run_cross_validation()
