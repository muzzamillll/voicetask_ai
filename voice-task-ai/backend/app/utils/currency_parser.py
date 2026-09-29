"""
Pakistani currency expression parser.

Converts phrases like "25 hazar", "25k", "pachees hazar", "2 lakh",
"1.5 lakh", "50 thousand", "Rs 25,000", "25,000 rupees" into a normalized
{"value": <float>, "currency": "PKR"}.

Never converts currencies — everything here is assumed PKR unless another
currency is explicitly and unambiguously stated in the text (out of scope
for this MVP; the schema always reports "PKR" per the project spec).
"""
import re

# Roman Urdu number words 1-99 — enough to catch common spoken amounts
# like "pachees hazar" (25 thousand), "pachas hazar" (50 thousand).
_ROMAN_NUMBER_WORDS = {
    "ek": 1, "do": 2, "teen": 3, "char": 4, "paanch": 5, "panch": 5,
    "chey": 6, "che": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
    "gyarah": 11, "barah": 12, "terah": 13, "chaudah": 14, "pandrah": 15,
    "solah": 16, "satrah": 17, "atharah": 18, "unnees": 19, "bees": 20,
    "pachees": 25, "pachis": 25, "tees": 30, "paintees": 35, "chalees": 40,
    "chalis": 40, "pachas": 50, "pchas": 50, "sath": 60, "sathar": 70,
    "assi": 80, "nabbe": 90,
}

_MULTIPLIER_WORDS = {
    "hazar": 1_000, "hazaar": 1_000, "thousand": 1_000,
    "lakh": 100_000, "lac": 100_000,
    "crore": 10_000_000,
    "k": 1_000,
}

# Rs / PKR / rupee(s) prefix or suffix with a plain number, possibly with commas.
_PLAIN_AMOUNT_RE = re.compile(
    r"(?:rs\.?\s*)?([\d,]+(?:\.\d+)?)\s*(?:rupees?|rs\.?|pkr)?", re.IGNORECASE
)

_NUMBER_WITH_MULTIPLIER_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(hazar|hazaar|thousand|lakh|lac|crore|k)\b", re.IGNORECASE
)


def _try_roman_words(text: str) -> float | None:
    """Handles patterns like 'pachees hazar', 'do lakh'."""
    words = text.lower().split()
    for i, word in enumerate(words):
        if word in _ROMAN_NUMBER_WORDS and i + 1 < len(words):
            next_word = words[i + 1].strip(".,")
            if next_word in _MULTIPLIER_WORDS:
                return _ROMAN_NUMBER_WORDS[word] * _MULTIPLIER_WORDS[next_word]
    return None


def parse_currency(text: str) -> dict | None:
    """
    Extracts the first recognizable PKR amount from text.
    Returns {"value": float, "currency": "PKR"} or None if nothing found.
    """
    if not text:
        return None

    lowered = text.lower()

    # 1. Digit + multiplier word: "25 hazar", "1.5 lakh", "25k"
    match = _NUMBER_WITH_MULTIPLIER_RE.search(lowered)
    if match:
        number = float(match.group(1))
        multiplier = _MULTIPLIER_WORDS[match.group(2)]
        return {"value": number * multiplier, "currency": "PKR"}

    # 2. Roman number word + multiplier word: "pachees hazar", "do lakh"
    roman_value = _try_roman_words(lowered)
    if roman_value is not None:
        return {"value": float(roman_value), "currency": "PKR"}

    # 3. Plain "Rs 25,000" / "25,000 rupees" style — only match if a
    # currency cue (rs/pkr/rupee) is actually present, to avoid treating
    # unrelated numbers (dates, phone numbers) as amounts.
    if re.search(r"\brs\.?\b|\brupees?\b|\bpkr\b", lowered):
        match = _PLAIN_AMOUNT_RE.search(lowered)
        if match:
            number_str = match.group(1).replace(",", "")
            try:
                return {"value": float(number_str), "currency": "PKR"}
            except ValueError:
                pass

    return None
