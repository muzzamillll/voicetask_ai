"""
Google Gemini integration — replaces local Whisper (transcription) and
local Ollama (LLM extraction) with a single free cloud API.

Uses plain REST calls via httpx rather than Google's SDK, to avoid an
extra heavy dependency and its install friction — httpx is already a
project dependency.

Kept in its own module so the rest of the app (transcription_service.py,
extraction_service.py) only depends on simple function signatures —
swapping providers again later means changing this file only.
"""
import base64
import mimetypes
from pathlib import Path

import httpx

from app.config import settings

_GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={api_key}"
)

# Gemini's officially documented supported audio types. m4a/webm aren't
# on that list but are close enough in practice (m4a is AAC-in-MP4,
# webm commonly carries Opus) that Gemini generally still handles them —
# if a particular file fails, converting it to .wav or .mp3 first
# (e.g. with ffmpeg, already installed for Whisper) is the fallback.
_MIME_TYPE_OVERRIDES = {
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",  # WhatsApp voice notes are Opus audio in an Ogg container
    ".oga": "audio/ogg",  # Telegram voice messages
}


class GeminiError(Exception):
    """Raised when a Gemini API call fails or returns an unusable response."""


def _require_api_key() -> None:
    if not settings.GEMINI_API_KEY:
        raise GeminiError(
            "GEMINI_API_KEY is not set. Get a free key from "
            "https://aistudio.google.com/apikey and add it to your .env file."
        )


def _call_gemini(parts: list[dict], force_json: bool = False) -> str:
    _require_api_key()
    url = _GENERATE_URL.format(model=settings.GEMINI_MODEL, api_key=settings.GEMINI_API_KEY)

    body = {"contents": [{"parts": parts}]}
    if force_json:
        body["generationConfig"] = {"response_mime_type": "application/json"}

    response = httpx.post(url, json=body, timeout=120.0)
    if response.status_code != 200:
        raise GeminiError(f"Gemini API error {response.status_code}: {response.text[:500]}")

    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise GeminiError(f"Unexpected Gemini response shape: {data}") from exc


def transcribe_audio(audio_path: str, language_hint: str | None = None) -> dict:
    """
    Transcribes audio via Gemini. Matches the same interface the local
    Whisper service used, so transcription_service.py didn't need to change:
        {"text": "<raw transcript>", "language": "<display name or code>"}
    """
    path = Path(audio_path)
    mime_type = _MIME_TYPE_OVERRIDES.get(
        path.suffix.lower(), mimetypes.guess_type(str(path))[0] or "audio/mp3"
    )
    audio_b64 = base64.b64encode(path.read_bytes()).decode("ascii")

    language_instruction = (
        f" The speaker is expected to be speaking {language_hint}."
        if language_hint
        else ""
    )
    prompt = (
        "Transcribe this audio exactly as spoken. Preserve the original "
        "language and script — do NOT translate it. If the speech is Urdu, "
        "Sindhi, or Siraiki, write it in its native Perso-Arabic script. "
        "If it's Roman Urdu/Sindhi/Siraiki (those languages' words typed in "
        "Latin letters), write it that way, not in Arabic script. Return "
        "ONLY the transcript text, with no commentary, labels, or quotation "
        "marks around it." + language_instruction
    )

    parts = [
        {"text": prompt},
        {"inline_data": {"mime_type": mime_type, "data": audio_b64}},
    ]
    text = _call_gemini(parts).strip()
    return {"text": text, "language": language_hint or ""}


def call_llm(prompt: str) -> str:
    """
    Text-only Gemini call for LLM extraction (Phase 6). Matches the same
    interface extraction_service.py originally used for Ollama, so only
    this module needed to change — not the extraction/validation logic.
    """
    parts = [{"text": prompt}]
    return _call_gemini(parts, force_json=True)


def translate_text(text: str) -> dict:
    """
    Translates a transcript into both English and Urdu, regardless of
    the source language (if the source already IS English or Urdu, that
    "translation" is effectively just a clean rendering of the original).

    Returns: {"english": "...", "urdu": "..."}
    """
    prompt = (
        "Translate the following text into BOTH English and Urdu (Urdu in "
        "native Perso-Arabic script). If the text is already in one of "
        "these languages, still provide a natural version in the other "
        "one — for the language it's already in, you may return the "
        "original text unchanged.\n\n"
        "Return ONLY a JSON object with exactly this shape, no other text:\n"
        '{"english": "...", "urdu": "..."}\n\n'
        f'TEXT: "{text}"'
    )
    parts = [{"text": prompt}]
    raw = _call_gemini(parts, force_json=True)

    import json
    import re

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise GeminiError(f"No JSON object found in translation response: {raw[:200]!r}")
    data = json.loads(match.group(0))
    return {"english": data.get("english", ""), "urdu": data.get("urdu", "")}
