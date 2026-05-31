"""Tests for Arabic voice command parser."""

import pytest
from .voice_arabic import (
    normalize_arabic,
    extract_numbers,
    detect_dialect,
    parse_arabic_intent,
    arabic_text_to_ssml,
    _is_arabic_text,
)


class TestNormalizeArabic:
    def test_removes_tashkeel(self):
        text = "حَالَةُ التَّصْرِيحِ"
        result = normalize_arabic(text)
        assert "\u064B" not in result  # No fatha
        assert "حاله التصريح" in result  # ta marbuta normalized to ه

    def test_normalizes_alef_variants(self):
        text = "أريد إجازة آخر"
        result = normalize_arabic(text)
        assert "\u0623" not in result  # No hamza on alef
        assert "\u0625" not in result
        assert "\u0622" not in result

    def test_applies_dialect_map(self):
        text = "عايز أقدم شكوى"
        result = normalize_arabic(text)
        assert "أريد" in result  # Egyptian "عايز" → "أريد"

    def test_gulf_dialect(self):
        text = "أبي أحجز موعد"
        result = normalize_arabic(text)
        assert "أريد" in result  # Gulf "أبي" → "أريد"


class TestExtractNumbers:
    def test_arabic_number_words(self):
        text = "عايز أقدم شكوى بعد خمسة أيام"
        numbers = extract_numbers(text)
        assert 5 in numbers

    def test_eastern_numerals(self):
        text = "رقم التصريح ١٢٣٤"
        numbers = extract_numbers(text)
        assert 1234 in numbers

    def test_western_numerals(self):
        text = "permit number 5678"
        numbers = extract_numbers(text)
        assert 5678 in numbers

    def test_multiple_numbers(self):
        text = "عشرين وثلاثون"
        numbers = extract_numbers(text)
        assert 20 in numbers
        assert 30 in numbers


class TestDetectDialect:
    def test_egyptian(self):
        text = "إزاي أقدم شكوى"
        dialect = detect_dialect(text)
        assert dialect == "ar-EG"

    def test_gulf(self):
        text = "شلون أبي أحجز"
        dialect = detect_dialect(text)
        assert dialect == "ar-AE"

    def test_levantine(self):
        text = "كيفك بدي موعد"
        dialect = detect_dialect(text)
        assert dialect == "ar-LB"

    def test_standard_fallback(self):
        text = "أريد المساعدة"
        dialect = detect_dialect(text)
        assert dialect == "ar-SA"


class TestParseArabicIntent:
    def test_services_intent(self):
        result = parse_arabic_intent("شو الخدمات المتاحة")
        assert result is not None
        assert result.intent == "city.services.list"
        assert result.confidence > 0.5
        assert result.language == "ar-LB"  # Levantine "شو"

    def test_permit_intent(self):
        result = parse_arabic_intent("أبي أشوف حالة التصريح ١٢٣٤")
        assert result is not None
        assert result.intent == "permit.status.check"
        assert result.entities.get("permit_id") == "1234"

    def test_prayer_intent(self):
        result = parse_arabic_intent("متى مواقيت الصلاة اليوم")
        assert result is not None
        assert result.intent == "prayer.times.today"

    def test_waste_intent(self):
        result = parse_arabic_intent("متى يجون ياخذون القمامة")
        assert result is not None
        assert result.intent == "waste.schedule"

    def test_complaint_intent(self):
        result = parse_arabic_intent("عندي شكوى عن الطريق")
        assert result is not None
        assert result.intent == "complaint.file"
        assert result.entities.get("category") == "road"

    def test_non_arabic_returns_none(self):
        result = parse_arabic_intent("hello world")
        assert result is None

    def test_help_fallback(self):
        result = parse_arabic_intent("أريد المساعدة")
        assert result is not None
        assert result.intent == "help.general"


class TestArabicTextToSSML:
    def test_generates_ssml(self):
        text = "مرحبا بك في CityOS"
        ssml = arabic_text_to_ssml(text, "ar-SA")
        assert '<speak xml:lang="ar-SA">' in ssml
        assert '<prosody rate="90%">' in ssml
        assert "مرحبا بك" in ssml

    def test_generates_ssml_default_lang(self):
        text = "مرحبا"
        ssml = arabic_text_to_ssml(text)
        assert '<speak xml:lang="ar-SA">' in ssml


class TestIsArabicText:
    def test_detects_arabic(self):
        assert _is_arabic_text("مرحبا") is True

    def test_detects_mixed(self):
        assert _is_arabic_text("مرحبا hello") is True

    def test_rejects_english(self):
        assert _is_arabic_text("hello world") is False

    def test_rejects_empty(self):
        assert _is_arabic_text("") is False
