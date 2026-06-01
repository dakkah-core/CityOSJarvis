"""Prompt injection detection and prevention for CityOSJarvis.

Scans user prompts for known jailbreak patterns, prompt injection attacks,
and harmful content before sending to LLM providers.

Integrates with CityOSAuthMiddleware for tenant-scoped policy enforcement.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PromptGuardResult:
    """Result of a prompt security scan."""

    is_safe: bool
    risk_score: float  # 0.0 - 1.0
    matched_patterns: list[str]
    reason: str
    action: str  # "allow", "warn", "block"


class PromptGuard:
    """Detects prompt injection, jailbreak attempts, and harmful content.

    Uses a combination of:
    - Keyword/phrase pattern matching
    - Structural analysis (repeated delimiters, role confusion)
    - Unicode obfuscation detection
    - Configurable per-tenant policies
    """

    # High-confidence injection patterns (immediate block)
    BLOCK_PATTERNS: list[tuple[str, float]] = [
        # English jailbreaks
        (r"ignore\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions|prompts)", 1.0),
        (r"ignore\s+(?:the\s+)?(?:above|previous)\s+(?:instructions?|prompts?|guidelines?)", 1.0),
        (r"disregard\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions|prompts)", 1.0),
        (r"forget\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions|prompts)", 1.0),
        (r"you\s+are\s+now\s+(?:in\s+)?(?:DAN|dan|jailbreak|developer)\s+mode", 1.0),
        (r"DAN\s+mode\s+(?:enabled|activated|on)", 1.0),
        (r"(?:do\s+anything\s+now|DAN)\s*[:\-]", 1.0),
        (r"(?:enable|activate|turn\s+on)\s+(?:developer|admin|root|system)\s+mode", 1.0),
        (r"(?:developer|admin|root|system)\s+mode\s*(?:enabled|activated|on)", 1.0),
        (r"simulate\s+(?:being|acting\s+as)\s+(?:DAN|an?\s+unrestricted)\s+(?:AI|model)", 1.0),
        (r"(?:hypothetically|theoretically|imagine)\s+.*(?:no\s+restrictions|no\s+limits|unfiltered)", 0.9),
        (r"(?:pretend|act\s+as\s+if)\s+.*(?:no\s+ethical|no\s+safety|no\s+content)\s+(?:guidelines|restrictions|filters)", 0.9),
        (r"(?:bypass|circumvent|override)\s+(?:content\s+)?(?:safety|ethical)?\s*(?:filters|guidelines|restrictions)", 0.95),
        (r"(?:new|fresh|clean)\s+(?:instructions|prompt|context)\s*[:\-]", 0.85),
        (r"\[\s*(?:system|admin|developer)\s*\]\s*[:\-]", 0.9),
        (r"<\s*(?:system|admin|developer)\s*>\s*[:\-]", 0.9),
        (r"\{\s*(?:system|admin|developer)\s*\}\s*[:\-]", 0.9),
        (r"(?:role|persona)\s*[:\-]\s*(?:unrestricted|uncensored|unfiltered)", 0.9),
        # Arabic jailbreaks
        (r"تجاهل\s+(?:كل\s+)?(?:التعليمات|الأوامر)\s+(?:السابقة|السابقة)", 1.0),
        (r"انسَ\s+(?:كل\s+)?(?:التعليمات|الأوامر)\s+(?:السابقة|السابقة)", 1.0),
        (r"أنت\s+الآن\s+في\s+(?:وضع|mode)\s+(?:DAN|دان|غير\s+مقيد)", 1.0),
        (r"(افترض|تخيل)\s+.*(?:لا\s+قيود|لا\s+حدود|غير\s+مفلتر)", 0.9),
        (r"(تجاوز|تخطي)\s+(?:فلاتر|قيود)\s+(?:الأمان|المحتوى|الأخلاقية)", 0.95),
        # Unicode obfuscation
        (r"[\u200B-\u200D\uFEFF]", 0.7),  # Zero-width characters
        (r"[\uFF01-\uFF5E]", 0.5),  # Full-width ASCII
        (r"[\u01D5-\u01DC]", 0.5),  # Homoglyphs
        # Delimiter abuse
        (r"={10,}", 0.6),
        (r"-{10,}", 0.6),
        (r"#{10,}", 0.6),
        (r"\*{10,}", 0.6),
        (r"`{10,}", 0.6),
        (r"\|{10,}", 0.6),
        # Role confusion
        (r"^(?:user|human|assistant|ai|bot)\s*[:\-]\s*", 0.7),
        (r"\n\s*(?:user|human|assistant|ai|bot)\s*[:\-]\s*", 0.7),
        # Multi-language injection markers
        (r"(?:Prompt|prompt)\s*Injection", 0.95),
        (r"(?:Jailbreak|jailbreak)\s*(?:mode|activated|enabled)", 0.95),
    ]

    # Warning patterns (log but allow with elevated monitoring)
    WARN_PATTERNS: list[tuple[str, float]] = [
        (r"(?:write|generate|create)\s+.*(?:malware|virus|trojan|ransomware|exploit)", 0.7),
        (r"(?:how\s+to|steps\s+to)\s+.*(?:hack|crack|bypass|exploit)\s+.*(?:security|password|auth|network|system)", 0.7),
        (r"(?:fake|forged|counterfeit)\s+.*(?:ID|passport|document|certificate)", 0.6),
        (r"(?:steal|theft|fraud|scam|phishing)\s+.*(?:money|data|identity|credentials)", 0.6),
        (r"(?:bomb|weapon|explosive|poison|toxin)\s+.*(?:make|build|create|recipe)", 0.8),
        (r"(?:child|minor)\s+.*(?:sexual|porn|abuse|exploitation)", 0.9),
        (r"(?:self-harm|suicide|kill\s+myself|end\s+my\s+life)", 0.8),
    ]

    def __init__(self, block_threshold: float = 0.8, warn_threshold: float = 0.5) -> None:
        self.block_threshold = block_threshold
        self.warn_threshold = warn_threshold

    def scan(self, prompt: str, tenant_id: str = "default") -> PromptGuardResult:
        """Scan a user prompt for security issues.

        Args:
            prompt: The user prompt to scan
            tenant_id: Tenant ID for policy scoping

        Returns:
            PromptGuardResult with safety verdict and action
        """
        if not prompt or not prompt.strip():
            return PromptGuardResult(
                is_safe=True,
                risk_score=0.0,
                matched_patterns=[],
                reason="Empty prompt",
                action="allow",
            )

        matched: list[str] = []
        max_score = 0.0
        reasons: list[str] = []

        # Check block patterns
        for pattern, score in self.BLOCK_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                matched.append(pattern)
                max_score = max(max_score, score)
                reasons.append(f"Block pattern matched: {pattern[:50]}...")

        # Check warn patterns
        for pattern, score in self.WARN_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                matched.append(pattern)
                max_score = max(max_score, score)
                reasons.append(f"Warn pattern matched: {pattern[:50]}...")

        # Structural analysis
        structural_score = self._structural_analysis(prompt)
        if structural_score > 0:
            max_score = max(max_score, structural_score)
            reasons.append(f"Structural anomaly detected (score: {structural_score:.2f})")

        # Normalize score
        max_score = min(max_score, 1.0)

        # Determine action
        if max_score >= self.block_threshold:
            action = "block"
            is_safe = False
        elif max_score >= self.warn_threshold:
            action = "warn"
            is_safe = True
        else:
            action = "allow"
            is_safe = True

        reason = "; ".join(reasons) if reasons else "No issues detected"

        logger.info(
            "PromptGuard scan: tenant=%s action=%s score=%.2f patterns=%d",
            tenant_id,
            action,
            max_score,
            len(matched),
        )

        # Record prompt guard metrics
        try:
            from openjarvis.cityos.metrics import PROMPT_GUARD_SCANS, PROMPT_GUARD_SCORE
            PROMPT_GUARD_SCANS.labels(tenant_id=tenant_id, action=action).inc()
            PROMPT_GUARD_SCORE.labels(tenant_id=tenant_id).observe(max_score)
        except Exception:
            pass

        return PromptGuardResult(
            is_safe=is_safe,
            risk_score=max_score,
            matched_patterns=matched,
            reason=reason,
            action=action,
        )

    def _structural_analysis(self, prompt: str) -> float:
        """Analyze prompt structure for anomalies."""
        score = 0.0

        # Excessive repetition of delimiters
        delimiter_count = sum(1 for c in prompt if c in "|=-`#*")
        if delimiter_count > len(prompt) * 0.3:
            score = max(score, 0.5)

        # Excessive newlines (possible multi-prompt injection)
        newline_count = prompt.count("\n")
        if newline_count > 20:
            score = max(score, 0.4)

        # Very long prompt (possible context stuffing)
        if len(prompt) > 8000:
            score = max(score, 0.3)

        # High ratio of non-printable characters
        non_printable = sum(1 for c in prompt if ord(c) < 32 and c not in "\n\r\t")
        if non_printable > len(prompt) * 0.05:
            score = max(score, 0.6)

        # Mixed script attack (e.g., Latin + Cyrillic homoglyphs)
        scripts = set()
        for c in prompt:
            o = ord(c)
            if 0x0041 <= o <= 0x007A:  # Latin
                scripts.add("latin")
            elif 0x0400 <= o <= 0x04FF:  # Cyrillic
                scripts.add("cyrillic")
            elif 0x0600 <= o <= 0x06FF:  # Arabic
                scripts.add("arabic")
        if len(scripts) > 2:
            score = max(score, 0.5)

        return score

    def sanitize(self, prompt: str) -> str:
        """Remove known injection markers from prompt.

        This is a last-resort defense — prefer blocking over sanitizing.
        """
        sanitized = prompt
        # Remove zero-width characters
        sanitized = re.sub(r"[\u200B-\u200D\uFEFF]", "", sanitized)
        # Normalize repeated delimiters
        sanitized = re.sub(r"={10,}", "===", sanitized)
        sanitized = re.sub(r"-{10,}", "---", sanitized)
        sanitized = re.sub(r"#{10,}", "###", sanitized)
        sanitized = re.sub(r"\*{10,}", "***", sanitized)
        sanitized = re.sub(r"`{10,}", "```", sanitized)
        sanitized = re.sub(r"\|{10,}", "|||", sanitized)
        return sanitized.strip()
