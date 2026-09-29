"""
LLM structured extraction, via Google Gemini.

Deliberately thin and provider-swappable: everything specific to "how we
call the model" lives in call_llm(). Swapping providers again later means
rewriting this one function only — prompts.py and the Pydantic schema
stay the same.
"""
import json
import re

from pydantic import ValidationError

from app.schemas.extraction import ExtractionResult
from app.ai.gemini_service import call_llm, GeminiError  # noqa: F401 (re-exported for callers)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


class ExtractionError(Exception):
    """Raised when the LLM response can't be parsed/validated as JSON."""


def _extract_json_block(raw_text: str) -> dict:
    """
    Models occasionally wrap JSON in markdown fences or add stray text
    despite instructions. This pulls out the first {...} block found and
    parses it, rather than crashing on the surrounding text.
    """
    match = _JSON_BLOCK_RE.search(raw_text)
    if not match:
        raise ExtractionError(f"No JSON object found in LLM response: {raw_text[:200]!r}")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"LLM returned invalid JSON: {exc}") from exc


def extract_structured_data(prompt: str) -> ExtractionResult:
    """
    Runs the full extraction step: call the LLM, parse its JSON, validate
    it against ExtractionResult. Raises ExtractionError on any failure —
    callers (the API layer) turn that into a proper HTTP error rather than
    letting a bad LLM response crash the app.
    """
    try:
        raw_text = call_llm(prompt)
    except GeminiError as exc:
        raise ExtractionError(str(exc)) from exc

    data = _extract_json_block(raw_text)

    try:
        return ExtractionResult.model_validate(data)
    except ValidationError as exc:
        raise ExtractionError(f"LLM JSON didn't match the expected schema: {exc}") from exc
