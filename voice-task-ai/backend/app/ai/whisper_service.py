"""
Local Whisper speech-to-text.

The model is loaded lazily and cached in-process (loading it is slow —
several seconds to tens of seconds depending on model size — so we do it
once, not on every request).

Kept deliberately thin: whisper_service.py only knows how to run Whisper.
Higher-level orchestration (updating DB status, calling the LLM next)
lives in transcription_service.py and the API layer.
"""
import whisper

from app.config import settings

_model = None  # module-level cache

# A short domain hint fed to Whisper as "initial_prompt" — it biases the
# model's vocabulary/style toward what it's likely hearing, without
# forcing any specific words into the output. Mixing Roman Urdu, Urdu
# script, and common domain terms (money, dates, names) nudges Whisper
# toward this app's actual use case: informal Pakistani task/order/
# payment voice notes, rather than generic dictation.
_DOMAIN_PROMPT = (
    "Ali ko kal paanch baje phone karna hai. "
    "پچیس ہزار روپے ادا کرنے ہیں۔ "
    "Order confirm karo aur delivery Friday ko bhejo. "
    "Payment due hai, Rs 25,000."
)


def get_model():
    global _model
    if _model is None:
        _model = whisper.load_model(settings.WHISPER_MODEL_SIZE)
    return _model


def transcribe_audio(audio_path: str, language_hint: str | None = None) -> dict:
    """
    Runs Whisper on the given audio file.

    language_hint: an optional ISO 639-1 code ("ur", "sd", "en") to tell
    Whisper what language to expect instead of auto-detecting. This
    matters a lot for accuracy — Whisper's audio-based language
    auto-detection is unreliable for lower-resource languages like Urdu
    and Sindhi (it frequently guesses Hindi instead), and forcing the
    right language skips that guesswork entirely, often dramatically
    improving transcription quality.

    Returns:
        {
            "text": "<raw transcript>",
            "language": "<ISO 639-1 code Whisper detected/used, e.g. 'ur', 'en'>",
        }
    """
    model = get_model()
    kwargs = {
        "initial_prompt": _DOMAIN_PROMPT,
        # Prevents a well-known Whisper failure mode where it gets stuck
        # looping the same phrase over and over (often triggered by
        # silence/noise/music before speech starts). Each segment is
        # decoded independently instead of being conditioned on what was
        # just transcribed, which is what lets loops spiral in the first
        # place.
        "condition_on_previous_text": False,
    }
    if language_hint:
        kwargs["language"] = language_hint
    result = model.transcribe(audio_path, **kwargs)
    return {
        "text": result.get("text", "").strip(),
        "language": result.get("language", language_hint or ""),
    }
