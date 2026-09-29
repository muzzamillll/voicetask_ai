"""
Phase 6 tests for LLM extraction logic.

These mock call_llm() directly, so they run instantly without needing
Ollama actually installed/running — they test our parsing/validation
logic, not Ollama itself.

Run with:
    pytest tests/test_extraction_service.py -v
"""
import pytest

from app.ai import extraction_service
from app.ai.extraction_service import extract_structured_data, ExtractionError
from app.ai.prompts import build_extraction_prompt
from datetime import datetime, timezone


VALID_RESPONSE = """{
  "intent": "task",
  "title": "Call Ali",
  "description": "",
  "task": "call Ali",
  "contact": {"name": "Ali", "phone": ""},
  "deadline": {"date": "2026-09-11", "time": "17:00", "datetime": "2026-09-11T17:00:00", "is_specific": true},
  "amount": {"value": 25000, "currency": "PKR"},
  "quantity": null,
  "location": "",
  "priority": "high",
  "status": "pending",
  "language": "Roman Urdu",
  "confidence": 0.92,
  "needs_clarification": false,
  "clarification_question": ""
}"""


def test_extract_valid_response(monkeypatch):
    monkeypatch.setattr(extraction_service, "call_llm", lambda prompt: VALID_RESPONSE)
    result = extract_structured_data("dummy prompt")
    assert result.intent.value == "task"
    assert result.contact.name == "Ali"
    assert result.amount.value == 25000
    assert result.deadline.is_specific is True


def test_extract_handles_markdown_fenced_json(monkeypatch):
    fenced = f"```json\n{VALID_RESPONSE}\n```"
    monkeypatch.setattr(extraction_service, "call_llm", lambda prompt: fenced)
    result = extract_structured_data("dummy prompt")
    assert result.contact.name == "Ali"


def test_extract_rejects_invalid_json(monkeypatch):
    monkeypatch.setattr(extraction_service, "call_llm", lambda prompt: "not json at all")
    with pytest.raises(ExtractionError):
        extract_structured_data("dummy prompt")


def test_extract_rejects_json_missing_required_shape(monkeypatch):
    # Valid JSON, but "contact" is a string instead of an object — should
    # fail Pydantic validation rather than silently accepting garbage.
    bad_shape = '{"intent": "task", "contact": "not an object"}'
    monkeypatch.setattr(extraction_service, "call_llm", lambda prompt: bad_shape)
    with pytest.raises(ExtractionError):
        extract_structured_data("dummy prompt")


def test_extract_applies_defaults_for_missing_fields(monkeypatch):
    minimal = '{"intent": "note"}'
    monkeypatch.setattr(extraction_service, "call_llm", lambda prompt: minimal)
    result = extract_structured_data("dummy prompt")
    assert result.intent.value == "note"
    assert result.contact.name == ""
    assert result.amount.value is None
    assert result.needs_clarification is False


def test_build_extraction_prompt_includes_transcript_and_datetime():
    ref = datetime(2026, 9, 10, tzinfo=timezone.utc)
    prompt = build_extraction_prompt("ali ko kal call karna hai", "Roman Urdu", ref)
    assert "ali ko kal call karna hai" in prompt
    assert "2026-09-10" in prompt
    assert "Roman Urdu" in prompt
