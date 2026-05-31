"""Arabic voice command parser for CityOSJarvis.

Handles:
- Arabic intent detection (transliterated + formal Arabic)
- Dialect normalization (Egyptian, Gulf, Levantine, Maghrebi)
- Number parsing (Arabic numerals + written numbers)
- Direction/location terms
- Common citizen service phrases
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ArabicIntent:
    """Parsed Arabic voice intent."""

    intent: str
    confidence: float
    entities: dict[str, Any]
    language: str  # "ar-SA", "ar-EG", "ar-AE", etc.
    original_text: str
    normalized_text: str


# Intent patterns mapped to Arabic phrases
_INTENT_PATTERNS = {
    "city.services.list": [
        r"خدمات المدينة",
        r"الخدمات المتاحة",
        r"شو الخدمات",
        r"خدمات",
        r"services",
    ],
    "permit.status.check": [
        r"حالة التصريح",
        r"حاله التصريح",
        r"التصاريح",
        r"رخصة البناء",
        r"building permit",
        r"permit",
    ],
    "prayer.times.today": [
        r"مواقيت الصلاة",
        r"مواقيت الصلاه",
        r"الصلاة",
        r"الصلاه",
        r"أوقات الصلاة",
        r"prayer times",
        r"salat",
    ],
    "waste.schedule": [
        r"جمع النفايات",
        r"القمامة",
        r"القمامه",
        r"النفايات",
        r"waste collection",
        r"trash",
    ],
    "traffic.report": [
        r"حركة المرور",
        r"ازدحام",
        r"حادث مروري",
        r"traffic",
        r"accident",
    ],
    "complaint.file": [
        r"شكوى",
        r"شكوي",
        r"أريد أشتكي",
        r"بلاغ",
        r"complaint",
    ],
    "appointment.schedule": [
        r"موعد",
        r"حجز",
        r"أريد موعد",
        r"appointment",
    ],
    "payment.check": [
        r"فاتورة",
        r"دفع",
        r"الرسوم",
        r"bill",
        r"payment",
    ],
    "help.general": [
        r"مساعدة",
        r"ساعدني",
        r"كيف",
        r"help",
    ],
}

# Number words in Arabic (0-100)
_ARABIC_NUMBERS = {
    "صفر": 0, "واحد": 1, "واحدة": 1, "اثنان": 2, "اثنين": 2, "ثلاثة": 3,
    "أربعة": 4, "خمسة": 5, "ستة": 6, "سبعة": 7, "ثمانية": 8, "تسعة": 9,
    "عشرة": 10, "عشرين": 20, "ثلاثين": 30, "ثلاثون": 30, "أربعين": 40, "أربعون": 40,
    "خمسين": 50, "خمسون": 50, "ستين": 60, "ستون": 60, "سبعين": 70, "سبعون": 70,
    "ثمانين": 80, "ثمانون": 80, "تسعين": 90, "تسعون": 90, "مئة": 100,
    "مائة": 100, "ألف": 1000,
    # Eastern Arabic numerals
    "٠": 0, "١": 1, "٢": 2, "٣": 3, "٤": 4,
    "٥": 5, "٦": 6, "٧": 7, "٨": 8, "٩": 9,
}

# Dialect normalization map (keys should match AFTER alef normalization)
_DIALECT_MAP = {
    # Egyptian dialect
    "إزاي": "كيف", "عايز": "أريد", "عاوز": "أريد",
    "مش": "لا", "كده": "هكذا", "بس": "فقط",
    "يابنى": "يا ابن", "يابنت": "يا بنت",
    # Gulf dialect
    "شلون": "كيف", "أبي": "أريد", "ابي": "أريد", "أبغى": "أريد", "ابغى": "أريد",
    "مو": "لا", "هال": "هذا", "ذاك": "ذلك",
    # Levantine
    "كيفك": "كيف حالك", "بدي": "أريد", "شو": "ما", "هيدا": "هذا",
    # Maghrebi
    "واش": "ما", "بغيت": "أريد", "خاصني": "أحتاج",
    "عندي": "لدي",
}


def normalize_arabic(text: str) -> str:
    """Normalize Arabic text: remove tashkeel, normalize alef variants, apply dialect map."""
    # Remove tashkeel (diacritics)
    text = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", text)

    # Normalize alef variants
    text = text.replace("\u0623", "\u0627")  # أ → ا
    text = text.replace("\u0625", "\u0627")  # إ → ا
    text = text.replace("\u0622", "\u0627")  # آ → ا
    text = text.replace("\u0671", "\u0627")  # ٱ → ا

    # Normalize ta marbuta
    text = text.replace("\u0629", "\u0647")  # ة → ه

    # Normalize yaa
    text = text.replace("\u0649", "\u064A")  # ى → ي

    # Apply dialect normalization
    words = text.split()
    normalized_words = [_DIALECT_MAP.get(w, w) for w in words]

    return " ".join(normalized_words)


def extract_numbers(text: str) -> list[int]:
    """Extract numeric values from Arabic text (both written and Eastern numerals)."""
    numbers = []
    words = text.split()

    for word in words:
        # Strip common prefixes like "و" (and)
        clean_word = word.lstrip("و")

        # Check Arabic number words
        if clean_word in _ARABIC_NUMBERS:
            numbers.append(_ARABIC_NUMBERS[clean_word])
        elif word in _ARABIC_NUMBERS:
            numbers.append(_ARABIC_NUMBERS[word])

        # Check Eastern Arabic numerals
        eastern_match = re.match(r"^[\u0660-\u0669]+$", clean_word)
        if eastern_match:
            eastern_str = clean_word.translate(str.maketrans(
                "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669",
                "0123456789"
            ))
            numbers.append(int(eastern_str))

        # Check Western numerals
        western_match = re.match(r"^\d+$", clean_word)
        if western_match:
            numbers.append(int(clean_word))

    return numbers


def detect_dialect(text: str) -> str:
    """Detect Arabic dialect based on keyword frequencies."""
    scores = {
        "ar-EG": 0,  # Egyptian
        "ar-AE": 0,  # Gulf
        "ar-SA": 0,  # Saudi/Standard
        "ar-LB": 0,  # Levantine
        "ar-MA": 0,  # Maghrebi
    }

    words = set(text.split())

    # Egyptian markers
    if words & {"إزاي", "عايز", "عاوز", "مش", "كده"}:
        scores["ar-EG"] += 3
    # Gulf markers
    if words & {"شلون", "أبي", "ابي", "أبغى", "ابغى", "مو", "هال"}:
        scores["ar-AE"] += 3
    # Levantine markers
    if words & {"كيفك", "بدي", "شو", "هيدا"}:
        scores["ar-LB"] += 3
    # Maghrebi markers
    if words & {"واش", "بغيت", "خاصني", "درت"}:
        scores["ar-MA"] += 3

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "ar-SA"  # Default to standard Arabic
    return best


def parse_arabic_intent(text: str) -> ArabicIntent | None:
    """Parse Arabic voice command into structured intent."""
    if not text or not _is_arabic_text(text):
        return None

    normalized = normalize_arabic(text)
    dialect = detect_dialect(text)
    numbers = extract_numbers(normalized)

    # Match against intent patterns
    best_intent = "help.general"
    best_score = 0.0
    matched_entities: dict[str, Any] = {}

    for intent, patterns in _INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                score = 0.8 if len(pattern) > 5 else 0.5
                if score > best_score:
                    best_score = score
                    best_intent = intent

    # Extract entities based on intent
    if best_intent == "permit.status.check":
        permit_id = _extract_permit_id(normalized)
        if permit_id:
            matched_entities["permit_id"] = permit_id
    elif best_intent == "appointment.schedule":
        if numbers:
            matched_entities["duration_minutes"] = numbers[0]
    elif best_intent == "complaint.file":
        category = _extract_complaint_category(normalized)
        if category:
            matched_entities["category"] = category

    # Confidence boost for longer matches
    confidence = min(best_score + (len(normalized) / 200), 1.0)

    return ArabicIntent(
        intent=best_intent,
        confidence=confidence,
        entities=matched_entities,
        language=dialect,
        original_text=text,
        normalized_text=normalized,
    )


def _is_arabic_text(text: str) -> bool:
    """Check if text contains Arabic script."""
    arabic_range = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
    return bool(arabic_range.search(text))


def _extract_permit_id(text: str) -> str | None:
    """Extract permit/building ID from text (Western or Eastern numerals)."""
    # Western numerals (use [0-9] not \d to avoid matching Eastern numerals)
    match = re.search(r"\b([0-9]{4,})\b", text)
    if match:
        return match.group(1)
    # Eastern Arabic numerals
    eastern_match = re.search(r"([\u0660-\u0669]{4,})", text)
    if eastern_match:
        return eastern_match.group(1).translate(str.maketrans(
            "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669",
            "0123456789"
        ))
    return None


def _extract_complaint_category(text: str) -> str | None:
    """Extract complaint category from Arabic text."""
    categories = {
        "road": ["طريق", "شارع", "حفرة", "إشارة"],
        "water": ["مياه", "صرف", "فاتورة المياه"],
        "noise": ["ضوضاء", "إزعاج", "بناء"],
        "waste": ["قمامة", "نفايات", "نظافة"],
    }
    for cat, keywords in categories.items():
        if any(kw in text for kw in keywords):
            return cat
    return None


def arabic_text_to_ssml(text: str, lang: str = "ar-SA") -> str:
    """Convert Arabic text to SSML with proper language and rate."""
    # Slow down speech slightly for Arabic clarity
    return f'<speak xml:lang="{lang}"><prosody rate="90%">{text}</prosody></speak>'
