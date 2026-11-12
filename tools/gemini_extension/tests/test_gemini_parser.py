"""
Unit tests for Gemini Cognitive Response Parser logic.
"""

import json
import re
import pytest

REQUIRED_SKILLS = [
    "attention",
    "working_memory",
    "logical_reasoning",
    "language_processing",
    "critical_thinking",
    "metacognition",
]


def clean_raw_text(text: str) -> str:
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"<thought>[\s\S]*?</thought>", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def extract_json_string(raw_text: str) -> str:
    cleaned = clean_raw_text(raw_text)
    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if code_block:
        return code_block.group(1).strip()
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return cleaned[first_brace : last_brace + 1].strip()
    return cleaned


def parse_and_validate(raw_text: str, expected_question_id: int | None = None) -> dict:
    json_str = extract_json_string(raw_text)
    data = json.loads(json_str)

    if expected_question_id is not None and "question_id" in data:
        assert int(data["question_id"]) == expected_question_id, (
            f"Stale output detected: got QID {data['question_id']} but expected {expected_question_id}"
        )

    scores = {}
    for skill in REQUIRED_SKILLS:
        assert skill in data, f"Missing skill: {skill}"
        val = round(float(data[skill]))
        assert 0 <= val <= 3, f"Score out of range: {val}"
        scores[skill] = val

    conf = float(data.get("confidence", 0.95))
    assert 0.0 <= conf <= 1.0, f"Confidence out of range: {conf}"

    return {
        "question_id": data.get("question_id", expected_question_id),
        "scores": scores,
        "confidence": conf,
        "short_rationale": data.get("short_rationale", "Grounded assessment."),
    }


def test_gemini_parse_clean_json():
    raw = """
    {
      "question_id": 12,
      "attention": 1,
      "working_memory": 2,
      "logical_reasoning": 3,
      "language_processing": 1,
      "critical_thinking": 1,
      "metacognition": 0,
      "confidence": 0.98,
      "short_rationale": "Direct algebraic deduction."
    }
    """
    res = parse_and_validate(raw, expected_question_id=12)
    assert res["question_id"] == 12
    assert res["scores"]["logical_reasoning"] == 3
    assert res["confidence"] == 0.98


def test_gemini_parse_markdown_fence():
    raw = """Sure, here is the cognitive evaluation:
```json
{
  "question_id": 30,
  "attention": 2,
  "working_memory": 2,
  "logical_reasoning": 2,
  "language_processing": 2,
  "critical_thinking": 1,
  "metacognition": 0,
  "confidence": 0.92,
  "short_rationale": "Word problem requiring multi-step arithmetic."
}
```
"""
    res = parse_and_validate(raw, expected_question_id=30)
    assert res["question_id"] == 30
    assert res["scores"]["language_processing"] == 2


def test_gemini_anti_stale_question_id_mismatch():
    raw = """
    {
      "question_id": 7,
      "attention": 1,
      "working_memory": 1,
      "logical_reasoning": 1,
      "language_processing": 1,
      "critical_thinking": 1,
      "metacognition": 0
    }
    """
    with pytest.raises(AssertionError, match="Stale output detected"):
        parse_and_validate(raw, expected_question_id=8)
