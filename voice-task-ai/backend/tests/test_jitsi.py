"""
Tests for Jitsi Meet link generation.

Run with:
    pytest tests/test_jitsi.py -v
"""
from app.integrations.jitsi import generate_meeting_link


def test_generates_valid_url():
    link = generate_meeting_link("AI Project Progress Meeting")
    assert link.startswith("https://meet.jit.si/")
    assert "AI-Project-Progress-Meeting" in link


def test_two_calls_produce_different_links():
    link1 = generate_meeting_link("Team Sync")
    link2 = generate_meeting_link("Team Sync")
    assert link1 != link2  # unique room per meeting, even with the same title


def test_handles_empty_title():
    link = generate_meeting_link("")
    assert link.startswith("https://meet.jit.si/VoiceTaskAI-meeting-")


def test_handles_non_latin_title():
    link = generate_meeting_link("علی سے میٹنگ")
    assert link.startswith("https://meet.jit.si/VoiceTaskAI-meeting-")


def test_no_spaces_or_special_characters_in_url():
    link = generate_meeting_link("Ali's Meeting @ 5pm!")
    assert " " not in link
    assert "@" not in link
    assert "!" not in link
    assert "'" not in link
