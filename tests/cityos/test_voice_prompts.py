"""Tests for voice prompt templates and SSML generation."""

from __future__ import annotations

from openjarvis.cityos.tenant import TenantContext
from openjarvis.cityos.voice_prompts import load_voice_prompt


class TestVoicePrompts:
    def test_load_voice_prompt_basic(self) -> None:
        prompt = load_voice_prompt("citizen-support")
        assert prompt is not None
        assert len(prompt) > 0
        assert "Voice Mode Constraints" in prompt

    def test_load_voice_prompt_with_tenant(self) -> None:
        tenant = TenantContext("t1", "global/sa/dakkah", ["ai_user"], "u1")
        prompt = load_voice_prompt("citizen-support", tenant=tenant)
        assert prompt is not None
        assert "Tenant Context" in prompt
        assert "t1" in prompt

    def test_load_voice_prompt_missing_persona(self) -> None:
        prompt = load_voice_prompt("nonexistent-persona")
        assert prompt is not None
        assert "Dakkah" in prompt  # Falls back to default

    def test_voice_constraints_included(self) -> None:
        prompt = load_voice_prompt("test")
        assert "concise" in prompt.lower() or "1-2 sentences" in prompt
        assert "markdown" in prompt.lower() or "lists" in prompt.lower()

    def test_arabic_instruction_included(self) -> None:
        prompt = load_voice_prompt("test")
        assert "Arabic" in prompt

    def test_tenant_path_in_prompt(self) -> None:
        tenant = TenantContext("my-tenant", "global.sa.dakkah", ["ai_user"], "u1")
        prompt = load_voice_prompt("test", tenant=tenant)
        assert "my-tenant" in prompt
        assert "global.sa.dakkah" in prompt

    def test_no_tenant_no_suffix(self) -> None:
        prompt = load_voice_prompt("test")
        assert "Tenant Context" not in prompt

    def test_empty_node_path_tenant(self) -> None:
        tenant = TenantContext("t1", None, ["ai_user"], "u1")
        prompt = load_voice_prompt("test", tenant=tenant)
        assert prompt is not None
