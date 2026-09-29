"""
Phase 5 tests — pure-function utilities, no database or audio needed.

Run with:
    pytest tests/test_phase5_utils.py -v
"""
from datetime import datetime

from app.utils.currency_parser import parse_currency
from app.utils.date_parser import parse_relative_date, parse_time_of_day, parse_deadline
from app.utils.language_detector import detect_language
from app.utils.transcript_cleaner import clean_transcript


# --- currency_parser ---

def test_currency_digit_plus_hazar():
    assert parse_currency("25 hazar dena hai") == {"value": 25000.0, "currency": "PKR"}


def test_currency_k_shorthand():
    assert parse_currency("send 25k please") == {"value": 25000.0, "currency": "PKR"}


def test_currency_roman_words():
    assert parse_currency("pachees hazar payment") == {"value": 25000.0, "currency": "PKR"}


def test_currency_lakh_decimal():
    assert parse_currency("1.5 lakh chahiye") == {"value": 150000.0, "currency": "PKR"}


def test_currency_do_lakh():
    assert parse_currency("do lakh ka order hai") == {"value": 200000.0, "currency": "PKR"}


def test_currency_rs_with_commas():
    assert parse_currency("Rs 25,000 due") == {"value": 25000.0, "currency": "PKR"}


def test_currency_none_when_absent():
    assert parse_currency("Ali ko call karna hai") is None


# --- date_parser ---

def test_relative_date_kal():
    ref = datetime(2026, 9, 10)  # Thursday
    assert parse_relative_date("kal milna hai", ref).isoformat() == "2026-09-11"


def test_relative_date_aaj():
    ref = datetime(2026, 9, 10)
    assert parse_relative_date("aaj hi karna hai", ref).isoformat() == "2026-09-10"


def test_relative_date_parson():
    ref = datetime(2026, 9, 10)
    assert parse_relative_date("parson aana", ref).isoformat() == "2026-09-12"


def test_relative_date_weekday_name():
    ref = datetime(2026, 9, 10)  # Thursday
    # next Friday should be the very next day here
    assert parse_relative_date("Friday ko milna hai", ref).isoformat() == "2026-09-11"


def test_relative_date_unrecognized_returns_none():
    ref = datetime(2026, 9, 10)
    assert parse_relative_date("random text with no date", ref) is None


def test_time_explicit_baje_evening_default():
    # bare "5 baje" with no am/pm defaults to evening per common usage
    t = parse_time_of_day("5 baje phone karna hai")
    assert t.hour == 17 and t.minute == 0


def test_time_explicit_pm():
    t = parse_time_of_day("5 PM call")
    assert t.hour == 17


def test_time_of_day_word():
    t = parse_time_of_day("shaam ko milna hai")
    assert t.hour == 18


def test_deadline_full_combo():
    ref = datetime(2026, 9, 10)
    result = parse_deadline("kal 5 baje milna hai", ref)
    assert result["date"] == "2026-09-11"
    assert result["time"] == "17:00"
    assert result["is_specific"] is True


def test_deadline_date_only_not_specific():
    ref = datetime(2026, 9, 10)
    result = parse_deadline("kal milna hai", ref)
    assert result["date"] == "2026-09-11"
    assert result["time"] is None
    assert result["is_specific"] is False


# --- language_detector ---

def test_detect_pure_english():
    assert detect_language("call ali tomorrow at 5 pm", "en") == "English"


def test_detect_roman_urdu_from_whisper_en_mislabel():
    # Whisper often reports "en" for Roman Urdu audio — the text itself
    # should still be recognized as Roman Urdu via marker words.
    text = "ali ko kal 5 baje phone karna hai"
    assert detect_language(text, "en") == "Roman Urdu"


def test_detect_mixed_code_switch():
    text = "ali ko kal meeting ke liye call karna hai aur payment bhi send karni hai"
    result = detect_language(text, "en")
    assert result in ("Roman Urdu", "Mixed")  # code-switched, heavy Urdu markers


def test_detect_urdu_script_trusts_whisper():
    assert detect_language("کل علی کو کال کرنا ہے", "ur") == "Urdu"


def test_detect_roman_siraiki():
    assert detect_language("meda kam aa, sadde ghar aavan", "") == "Roman Siraiki"


def test_detect_native_script_siraiki_needs_hint():
    # Without a hint, native-script Siraiki can't be reliably told apart
    # from Sindhi (they share most non-Urdu letters) — documented
    # limitation, not a bug. With an explicit hint it's trusted directly.
    native_text = "ڪالھ پنج وڳي فون ڪرڻو آھي"
    assert detect_language(native_text, "Siraiki") == "Siraiki"
    assert detect_language(native_text, "Sindhi") == "Sindhi"


# --- transcript_cleaner ---

def test_clean_removes_fillers():
    assert clean_transcript("umm ali ko matlab kal call karna hai") == "ali ko kal call karna hai"


def test_clean_collapses_whitespace():
    assert clean_transcript("ali   ko    kal call") == "ali ko kal call"


def test_clean_empty_string():
    assert clean_transcript("") == ""
