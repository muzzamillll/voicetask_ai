"""
Relative date/time parser for Pakistani voice notes.

Resolves expressions like "aaj", "kal", "parson", "aglay hafte", "Friday ko",
"subah", "5 baje", "5:30", "7 PM" into concrete dates/times — always
relative to a reference "now" that the caller supplies (per the project
spec: the backend must provide current date/time to the extraction layer
so relative dates resolve correctly; this module never guesses an exact
date from an ambiguous statement — it returns None instead of a wrong guess).
"""
import re
from datetime import datetime, date, time, timedelta

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

# Roman Urdu/Sindhi time-of-day words mapped to an approximate clock hour,
# used only when no explicit time (e.g. "5 baje") is given.
_TIME_OF_DAY_HOUR = {
    "subah": 9, "morning": 9,
    "dopahar": 13, "afternoon": 13,
    "shaam": 18, "evening": 18,
    "raat": 21, "night": 21,
}

_RELATIVE_DAY_OFFSETS = {
    "aaj": 0, "today": 0,
    "kal": 1, "tomorrow": 1,
    "parson": 2,
}

_CLOCK_TIME_RE = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|baje)?\b", re.IGNORECASE
)


def parse_relative_date(text: str, reference: datetime) -> date | None:
    """
    Resolves a relative day expression to a concrete date.
    Returns None if nothing recognizable is found — callers should treat
    that as "unknown", never guess.
    """
    lowered = text.lower()

    for word, offset in _RELATIVE_DAY_OFFSETS.items():
        if re.search(rf"\b{word}\b", lowered):
            return (reference + timedelta(days=offset)).date()

    if re.search(r"\baglay hafte\b|\bnext week\b", lowered):
        return (reference + timedelta(weeks=1)).date()

    # "Friday ko", "next Friday", or a bare weekday name -> the NEXT
    # occurrence of that weekday (today doesn't count as "next Friday").
    for name, weekday_index in _WEEKDAYS.items():
        if re.search(rf"\b{name}\b", lowered):
            days_ahead = (weekday_index - reference.weekday() + 7) % 7
            days_ahead = days_ahead or 7  # if today IS that weekday, jump a full week
            return (reference + timedelta(days=days_ahead)).date()

    return None


def parse_time_of_day(text: str) -> time | None:
    """
    Resolves an explicit or approximate time. Returns None if the text has
    no time cue at all (caller should treat the deadline as date-only).
    """
    lowered = text.lower()

    match = _CLOCK_TIME_RE.search(lowered)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        meridiem = (match.group(3) or "").lower()

        if 1 <= hour <= 12:
            if meridiem == "pm" and hour != 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0
            elif meridiem in ("", "baje") and hour < 8:
                # Ambiguous — a bare "5 baje" with no am/pm is usually
                # evening in everyday Pakistani speech (5 PM, not 5 AM).
                hour += 12
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return time(hour=hour, minute=minute)

    for word, hour in _TIME_OF_DAY_HOUR.items():
        if re.search(rf"\b{word}\b", lowered):
            return time(hour=hour, minute=0)

    return None


def parse_deadline(text: str, reference: datetime) -> dict:
    """
    Combines date + time resolution into the project's deadline schema:
        {"date": "YYYY-MM-DD" | None, "time": "HH:MM" | None,
         "datetime": ISO string | None, "is_specific": bool}
    is_specific is True only when BOTH a date and a time were resolved.
    """
    resolved_date = parse_relative_date(text, reference)
    resolved_time = parse_time_of_day(text)

    result = {
        "date": resolved_date.isoformat() if resolved_date else None,
        "time": resolved_time.strftime("%H:%M") if resolved_time else None,
        "datetime": None,
        "is_specific": False,
    }

    if resolved_date and resolved_time:
        result["datetime"] = datetime.combine(resolved_date, resolved_time).isoformat()
        result["is_specific"] = True
    elif resolved_date:
        result["datetime"] = datetime.combine(resolved_date, time(0, 0)).isoformat()

    return result
