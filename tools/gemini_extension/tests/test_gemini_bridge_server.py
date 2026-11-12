"""
Unit tests for Gemini Bridge Server and GeminiAnnotationManager.
"""

import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from tools.gemini_extension.bridge_server import (
    GeminiAnnotationManager,
    REQUIRED_SKILLS,
)


@pytest.fixture
def mock_questions_csv(tmp_path: Path) -> Path:
    csv_file = tmp_path / "mock_questions.csv"
    with csv_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["question_id", "question_text", "options_json", "image_paths_json", "has_images"],
        )
        writer.writeheader()
        # Question 0: Pure text
        writer.writerow({
            "question_id": "0",
            "question_text": "Calculate 15 + 27.",
            "options_json": json.dumps(["40", "42", "45"]),
            "image_paths_json": json.dumps([]),
            "has_images": "False",
        })
        # Question 1: Multimodal with diagram (MUST BE FILTERED OUT)
        writer.writerow({
            "question_id": "1",
            "question_text": "Find the area of the shaded triangle in the figure.",
            "options_json": json.dumps([]),
            "image_paths_json": json.dumps(["img/fig1.png"]),
            "has_images": "True",
        })
        # Question 2: Another text question
        writer.writerow({
            "question_id": "2",
            "question_text": "Solve for y: 4y - 8 = 12",
            "options_json": json.dumps(["5", "6"]),
            "image_paths_json": json.dumps([]),
            "has_images": "False",
        })
    return csv_file


def test_gemini_manager_strict_text_only_filtering(mock_questions_csv: Path, monkeypatch, tmp_path: Path):
    test_data_dir = tmp_path / "data"
    test_data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("tools.gemini_extension.bridge_server.DATA_DIR", test_data_dir)
    monkeypatch.setattr("tools.gemini_extension.bridge_server.ANNOTATIONS_FILE", test_data_dir / "gemini_annotations.jsonl")
    monkeypatch.setattr("tools.gemini_extension.bridge_server.FAILURES_FILE", test_data_dir / "gemini_failures.jsonl")
    monkeypatch.setattr("tools.gemini_extension.bridge_server.STATE_FILE", test_data_dir / "state.json")

    manager = GeminiAnnotationManager(questions_path=mock_questions_csv, target_count=500, text_only=True)

    stats = manager.get_stats()
    # Question 1 had an image, so it MUST be filtered out! Only questions 0 and 2 remain.
    assert stats["target_total"] == 2
    assert stats["completed"] == 0
    assert stats["remaining"] == 2

    # Verify no multimodal questions are present in target queue
    for q in manager.target_questions:
        assert q["has_images"] is False
        assert len(q["image_paths"]) == 0


def test_gemini_manager_get_next_and_prompt(mock_questions_csv: Path, monkeypatch, tmp_path: Path):
    test_data_dir = tmp_path / "data"
    test_data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("tools.gemini_extension.bridge_server.DATA_DIR", test_data_dir)
    monkeypatch.setattr("tools.gemini_extension.bridge_server.ANNOTATIONS_FILE", test_data_dir / "gemini_annotations.jsonl")
    monkeypatch.setattr("tools.gemini_extension.bridge_server.FAILURES_FILE", test_data_dir / "gemini_failures.jsonl")
    monkeypatch.setattr("tools.gemini_extension.bridge_server.STATE_FILE", test_data_dir / "state.json")

    manager = GeminiAnnotationManager(questions_path=mock_questions_csv)
    q = manager.get_next_question()
    assert q is not None
    assert q["question_id"] == 0

    prompt = manager.build_prompt(q)
    assert "Question ID: 0" in prompt
    assert "Calculate 15 + 27." in prompt
    assert "- 42" in prompt


def test_gemini_manager_record_success_and_state(mock_questions_csv: Path, monkeypatch, tmp_path: Path):
    test_data_dir = tmp_path / "data"
    test_data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("tools.gemini_extension.bridge_server.DATA_DIR", test_data_dir)
    monkeypatch.setattr("tools.gemini_extension.bridge_server.ANNOTATIONS_FILE", test_data_dir / "gemini_annotations.jsonl")
    monkeypatch.setattr("tools.gemini_extension.bridge_server.FAILURES_FILE", test_data_dir / "gemini_failures.jsonl")
    monkeypatch.setattr("tools.gemini_extension.bridge_server.STATE_FILE", test_data_dir / "state.json")

    manager = GeminiAnnotationManager(questions_path=mock_questions_csv)
    scores = {
        "attention": 1,
        "working_memory": 2,
        "logical_reasoning": 2,
        "language_processing": 1,
        "critical_thinking": 1,
        "metacognition": 0,
    }

    manager.record_success(
        question_id=0,
        scores=scores,
        confidence=0.96,
        short_rationale="Straightforward arithmetic addition.",
    )

    stats = manager.get_stats()
    assert stats["completed"] == 1
    assert stats["remaining"] == 1
    assert 0 in manager.completed_ids

    # Next question should be question 2 (skipping 1 which was multimodal)
    next_q = manager.get_next_question()
    assert next_q is not None
    assert next_q["question_id"] == 2


def test_gemini_manager_cross_validation_comparison(mock_questions_csv: Path, monkeypatch, tmp_path: Path):
    test_data_dir = tmp_path / "data"
    test_data_dir.mkdir(parents=True, exist_ok=True)
    annotations_file = test_data_dir / "gemini_annotations.jsonl"
    monkeypatch.setattr("tools.gemini_extension.bridge_server.DATA_DIR", test_data_dir)
    monkeypatch.setattr("tools.gemini_extension.bridge_server.ANNOTATIONS_FILE", annotations_file)
    monkeypatch.setattr("tools.gemini_extension.bridge_server.FAILURES_FILE", test_data_dir / "gemini_failures.jsonl")
    monkeypatch.setattr("tools.gemini_extension.bridge_server.STATE_FILE", test_data_dir / "state.json")

    manager = GeminiAnnotationManager(questions_path=mock_questions_csv)
    # Mock reference DeepSeek record for question 0
    manager.deepseek_annotations = {
        0: {
            "question_id": 0,
            "attention": 2,
            "working_memory": 2,
            "logical_reasoning": 2,
            "language_processing": 1,
            "critical_thinking": 1,
            "metacognition": 0,
        }
    }

    manager.record_success(
        question_id=0,
        scores={
            "attention": 2,
            "working_memory": 2,
            "logical_reasoning": 2,
            "language_processing": 1,
            "critical_thinking": 1,
            "metacognition": 0,
        },
        confidence=0.98,
        short_rationale="Exact agreement test.",
    )

    comp = manager.get_cross_validation_comparison()
    assert comp["overlap_count"] == 1
    assert comp["skills"]["logical_reasoning"]["exact_match_percent"] == 100.0
    assert comp["skills"]["logical_reasoning"]["mae"] == 0.0
