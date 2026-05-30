"""Data classification and compliance gate for CityOS.

Blocks requests containing protected health information (PHI),
personally identifiable information (PII), financial data, or
other regulated content before it reaches the AI model.

Aligned with CityOS compliance framework:
- docs/compliance/data-handling.md
- docs/compliance/authorization-audit.md
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """Result of classifying a request payload."""

    allowed: bool
    category: str  # "public", "internal", "restricted", "regulated", "blocked"
    reason: str | None
    redacted_payload: str | None


class ComplianceGate:
    """Gatekeeper that inspects requests before they reach the model.

    Usage:
        gate = ComplianceGate()
        result = gate.classify(user_message)
        if not result.allowed:
            return safe_error_response(result.reason)
    """

    # Patterns that indicate regulated or blocked content
    _BLOCKED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
        # National ID / Iqama patterns (Saudi Arabia)
        (re.compile(r"\b1\d{9}\b"), "Saudi national ID (Iqama)"),
        (re.compile(r"\b2\d{9}\b"), "Saudi national ID"),
        (re.compile(r"\b[12]-\d{9}\b"), "Saudi national ID (Iqama) with dash"),
        (re.compile(r"\b\d{2}-\d{7}\b"), "Saudi national ID (old format)"),
        # Credit card numbers (Luhn-ish)
        (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "Credit card number"),
        (re.compile(r"\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b"), "American Express card number"),
        # IBAN (SA prefix)
        (re.compile(r"\bSA\d{22}\b", re.IGNORECASE), "Saudi IBAN"),
        # Phone numbers (Saudi formats)
        (re.compile(r"\b05\d{8}\b"), "Saudi mobile number"),
        (re.compile(r"(?:^|\s|\+)966\s?5\d{8}\b"), "Saudi mobile number (intl)"),
        # Email addresses
        (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "Email address"),
        # API keys / secrets (heuristic)
        (re.compile(r"\b(sk-[a-zA-Z0-9]{20,})\b"), "API key pattern"),
        (re.compile(r"\b[ A-Za-z0-9_]{20,}=[A-Za-z0-9+/]{20,}\b"), "Encoded secret"),
        # JWT-looking tokens
        (re.compile(r"\beyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\b"), "JWT token pattern"),
    ]

    # Healthcare-related keywords that trigger restricted classification
    _HEALTH_KEYWORDS: list[str] = [
        "diagnosis", "prescription", "medication", "patient record",
        "medical history", "lab result", "blood test", "x-ray",
        "symptoms", "treatment plan", "clinical note", "hospital admission",
        "surgery", "operation",
        "تشخيص", "وصفة طبية", "دواء", "سجل مريض", "تاريخ طبي",
        "نتيجة مختبر", "اختبار دم", "أشعة", "أعراض", "خطة علاج", "ملاحظة سريرية",
        "عملية جراحية", "جراحة",
    ]

    def classify(self, payload: str) -> ClassificationResult:
        """Classify a request payload and return allow/deny decision."""
        if not payload or not isinstance(payload, str):
            return ClassificationResult(
                allowed=True,
                category="public",
                reason=None,
                redacted_payload=None,
            )

        # 1. Check blocked patterns (PII, financial, secrets)
        for pattern, description in self._BLOCKED_PATTERNS:
            if pattern.search(payload):
                logger.warning("Compliance gate blocked: %s detected", description)
                return ClassificationResult(
                    allowed=False,
                    category="blocked",
                    reason=f"Request contains {description}. For your privacy, this information cannot be processed automatically. Please contact your service center.",
                    redacted_payload=self._redact(payload, pattern),
                )

        # 2. Check health keywords (PHI indicator)
        lower_payload = payload.lower()
        health_matches = [kw for kw in self._HEALTH_KEYWORDS if kw.lower() in lower_payload]
        if health_matches:
            logger.warning("Compliance gate restricted: health keywords detected: %s", health_matches)
            return ClassificationResult(
                allowed=False,
                category="regulated",
                reason="Request appears to contain health-related information (PHI). This cannot be processed without explicit authorization. Please contact your healthcare provider.",
                redacted_payload=None,
            )

        # 3. Length-based heuristic for secrets
        if len(payload) > 5000 and self._looks_like_secret(payload):
            return ClassificationResult(
                allowed=False,
                category="blocked",
                reason="Request contains content that resembles secrets or credentials.",
                redacted_payload=None,
            )

        return ClassificationResult(
            allowed=True,
            category="public",
            reason=None,
            redacted_payload=None,
        )

    def _redact(self, payload: str, pattern: re.Pattern[str]) -> str:
        """Replace matched sensitive data with [REDACTED]."""
        return pattern.sub("[REDACTED]", payload)

    def _looks_like_secret(self, payload: str) -> bool:
        """Heuristic: long base64/hex strings may be secrets."""
        # If >30% of the payload is high-entropy (base64/hex-like), flag it
        words = payload.split()
        suspicious = [w for w in words if len(w) > 40 and w.isalnum()]
        if words and len(suspicious) / len(words) > 0.3:
            return True
        return False

    def classify_arabic(self, payload: str) -> ClassificationResult:
        """Arabic-specific classification with additional cultural context."""
        # Reuse base classification first
        result = self.classify(payload)
        if not result.allowed:
            return result

        # Arabic-specific PII: family book number, passport, etc.
        arabic_patterns: list[tuple[re.Pattern[str], str]] = [
            (re.compile(r"\b\d{10}\b"), "10-digit ID (possible passport/family book)"),
        ]
        for pattern, description in arabic_patterns:
            if pattern.search(payload):
                logger.warning("Compliance gate blocked (AR): %s detected", description)
                return ClassificationResult(
                    allowed=False,
                    category="blocked",
                    reason=f"الطلب يحتوي على {description}. لا يمكن معالجة هذه المعلومات تلقائياً. يرجى الاتصال بمركز الخدمة.",
                    redacted_payload=self._redact(payload, pattern),
                )

        return result
