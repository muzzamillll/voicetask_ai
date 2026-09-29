"""
Transcript cleaning.

Whisper output is generally clean, but conversational Pakistani voice notes
often contain filler words ("umm", "matlab", "yani", "acha") and irregular
spacing/punctuation. This does light-touch normalization only — it must
NEVER rewrite meaning, since the LLM extraction step (Phase 6) depends on
faithful text.
"""
import re

# Common filler/hesitation words across English, Urdu, and Roman Urdu/Sindhi.
# Kept short and conservative — better to under-remove than accidentally
# strip a real word (e.g. "acha" can also mean "okay/good" and carry meaning,
# so it's deliberately excluded).
FILLER_WORDS = {
    "umm", "um", "uh", "uhh", "hmm", "matlab", "yani", "like",
}

_WHITESPACE_RE = re.compile(r"\s+")


def clean_transcript(raw_text: str) -> str:
    """Collapses whitespace and strips standalone filler words."""
    if not raw_text:
        return ""

    tokens = raw_text.split()
    kept = [t for t in tokens if t.strip(".,!?").lower() not in FILLER_WORDS]
    cleaned = " ".join(kept)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned
