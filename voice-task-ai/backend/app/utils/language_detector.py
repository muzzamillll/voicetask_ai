"""
Refined language detection.

Audio-based language detection (whether from Whisper or Gemini) is
unreliable for Urdu, Sindhi, and especially Siraiki — these are
lower-resource languages that often get mislabeled by sound alone
(Urdu is frequently confused with Hindi; Siraiki and Sindhi share a lot
of their sound inventory and script). Two things compensate for this:

1. An explicit language hint (passed by the user via the dashboard's
   language dropdown, or the `language` query param) is trusted directly
   when given, since the person recording the voice note knows what
   language they spoke better than any audio classifier does.
2. When no hint is given, this module falls back to checking the
   TEXT of the transcript itself: native-script detection (is it
   actually written in Perso-Arabic script at all?) and, for Roman-
   script text, small keyword lists of common function words for each
   language, since those recur constantly regardless of topic.

Distinguishing Siraiki from Sindhi purely by which Perso-Arabic
characters appear is NOT reliable — the two scripts share most of their
extra (non-Urdu) letters, since both languages have implosive
consonants. Without an explicit hint, native-script Siraiki will most
likely be detected as Sindhi or Urdu. This is a known limitation, not a
bug — always pass a hint for Siraiki voice notes when possible.
"""
import re

# High-frequency Roman Urdu function words — chosen because they appear in
# almost any sentence regardless of topic, unlike nouns which vary widely.
ROMAN_URDU_MARKERS = {
    "hai", "hain", "ka", "ki", "ke", "ko", "se", "mein", "main", "aur",
    "kal", "aaj", "parson", "karna", "karo", "kiya", "diya", "dena",
    "lena", "milna", "bhai", "bhi", "nahi", "nahin", "kyun", "kaise",
    "acha", "theek", "paisa", "paise", "rupay", "hazar", "lakh", "baje",
    "wala", "wali", "jana", "aana", "chahiye",
}

# High-frequency Roman Sindhi function words.
ROMAN_SINDHI_MARKERS = {
    "aahe", "aahi", "ahis", "khe", "ji", "jo", "je", "ain", "ho", "huyo", "huyi",
    "acho", "vaje", "sifar", "rupiya", "paiso", "kan", "dah",
}

# High-frequency Roman Siraiki function words — distinct from Urdu/Sindhi
# where possible (e.g. "aa"/"e" for "is/are", "sadde"/"tuadi" possessives,
# "kithe" for "where", "kyu" without the "n").
ROMAN_SIRAIKI_MARKERS = {
    "aa", "e", "hoya", "hovay", "sadde", "sanu", "tuadi", "tuanu",
    "kithe", "kado", "keda", "aavan", "ghinna", "ditta", "farmavo",
    "meda", "mera", "asan", "tusan",
}

# Native-script languages we can recognize with a trusted hint. Accepts
# both full names (from Gemini/the dashboard) and legacy ISO codes, in
# case anything still passes those.
_HINT_TO_LANGUAGE = {
    "urdu": "Urdu", "ur": "Urdu",
    "sindhi": "Sindhi", "sd": "Sindhi",
    "siraiki": "Siraiki", "seraiki": "Siraiki",
    "english": "English", "en": "English",
}

_WORD_RE = re.compile(r"[a-zA-Z']+")

# Sindhi (and Siraiki) add several extra letters beyond the Urdu/Arabic-
# Persian alphabet (implosive consonants). This lets us tell native-script
# Sindhi/Siraiki text apart from plain Urdu text — but NOT reliably from
# each other, since they overlap heavily here. See module docstring.
_SINDHI_OR_SIRAIKI_CHARS = set("ڄڀٺٽٿڦڙڍڌڏڊڇڃڪڱ")

# Any character in these ranges means the text itself is written in
# Perso-Arabic script (used by Urdu, Sindhi, and Siraiki) — checking the
# produced TEXT directly sidesteps audio-based language ID being wrong.
_ARABIC_SCRIPT_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F]")


def _script_based_language(text: str) -> str | None:
    if any(ch in _SINDHI_OR_SIRAIKI_CHARS for ch in text):
        return "Sindhi"  # best guess without a hint — see module docstring
    if _ARABIC_SCRIPT_RE.search(text):
        return "Urdu"
    return None


def _token_ratio(text: str, markers: set[str]) -> float:
    words = [w.lower() for w in _WORD_RE.findall(text)]
    if not words:
        return 0.0
    hits = sum(1 for w in words if w in markers)
    return hits / len(words)


def detect_language(cleaned_text: str, language_hint: str) -> str:
    """
    Returns one of: "Urdu", "Roman Urdu", "Sindhi", "Roman Sindhi",
    "Siraiki", "Roman Siraiki", "English", "Mixed".

    language_hint: whatever language the caller told the transcription
    step to expect (e.g. "Urdu", "Siraiki", "en") — empty string if none
    was given (auto-detect).
    """
    hint_language = _HINT_TO_LANGUAGE.get((language_hint or "").strip().lower())

    # An explicit hint for a native-script language is trusted directly
    # when the text actually IS in Perso-Arabic script — this is exactly
    # the case script-based detection alone can't resolve (Siraiki vs
    # Sindhi), so the hint breaks the tie.
    if hint_language in ("Urdu", "Sindhi", "Siraiki") and _ARABIC_SCRIPT_RE.search(cleaned_text):
        return hint_language

    script_language = _script_based_language(cleaned_text)
    if script_language:
        return script_language

    urdu_ratio = _token_ratio(cleaned_text, ROMAN_URDU_MARKERS)
    sindhi_ratio = _token_ratio(cleaned_text, ROMAN_SINDHI_MARKERS)
    siraiki_ratio = _token_ratio(cleaned_text, ROMAN_SIRAIKI_MARKERS)

    # Thresholds are deliberately low: a couple of marker words in a short
    # voice note is already a strong signal, since these are function
    # words that recur constantly in natural speech.
    THRESHOLD = 0.12
    MIXED_CEILING = 0.35
    ratios = {
        "Roman Urdu": urdu_ratio,
        "Roman Sindhi": sindhi_ratio,
        "Roman Siraiki": siraiki_ratio,
    }
    above_threshold = {name: r for name, r in ratios.items() if r >= THRESHOLD}

    if len(above_threshold) > 1:
        return "Mixed"
    if above_threshold:
        (name, ratio), = above_threshold.items()
        # Heavy English mixed in with the markers reads as code-switching
        # rather than "pure" Roman speech in that language.
        return "Mixed" if ratio < MIXED_CEILING else name

    return hint_language or "English"
