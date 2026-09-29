"""
Prompt construction for LLM structured extraction.

Kept separate from extraction_service.py so the prompt can be tuned
independently of which model/provider actually calls it.
"""
from datetime import datetime

_SCHEMA_INSTRUCTIONS = """\
You extract structured information from informal Pakistani voice note \
transcripts (Urdu, Roman Urdu, Sindhi, Roman Sindhi, English, or code-switched \
mixes of these).

Return ONLY a single JSON object — no markdown fences, no explanation, no \
extra text before or after it — matching EXACTLY this shape:

{
  "intent": "task | reminder | order | payment | meeting | appointment | follow_up | note | unknown",
  "title": "",
  "description": "",
  "task": "",
  "contact": {"name": "", "phone": ""},
  "deadline": {"date": "", "time": "", "datetime": "", "is_specific": false},
  "amount": {"value": null, "currency": "PKR"},
  "quantity": null,
  "location": "",
  "priority": "low | medium | high",
  "status": "pending",
  "language": "Urdu | Roman Urdu | Sindhi | Roman Sindhi | Siraiki | Roman Siraiki | English | Mixed",
  "confidence": 0.0,
  "needs_clarification": false,
  "clarification_question": ""
}

Rules:
- NEVER invent information. If something isn't stated, use null or an empty string.
- Resolve relative dates/times (aaj, kal, parson, aglay hafte, Friday ko, subah, \
shaam, 5 baje, etc.) into concrete dates using the CURRENT DATETIME given below. \
If the statement is ambiguous, leave date/time fields empty rather than guessing.
- Normalize currency expressions (25 hazar, 25k, pachees hazar, 2 lakh, Rs 25,000, \
etc.) into a numeric PKR value. Do not convert to other currencies.
- If an important field for the intent is missing (e.g. a meeting with no time), \
set needs_clarification to true and write a short, specific clarification_question.
- confidence is your own estimate (0.0-1.0) of how correct this extraction is.
"""


def build_extraction_prompt(cleaned_transcript: str, detected_language: str, reference: datetime) -> str:
    return (
        f"{_SCHEMA_INSTRUCTIONS}\n"
        f"CURRENT DATETIME: {reference.isoformat()}\n"
        f"DETECTED LANGUAGE: {detected_language}\n"
        f"TRANSCRIPT: \"{cleaned_transcript}\"\n\n"
        f"JSON:"
    )
