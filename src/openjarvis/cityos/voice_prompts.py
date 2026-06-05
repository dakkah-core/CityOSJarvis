"""Voice-optimized system prompt loader for CityOS.

Voice mode appends constraints to base personas:
- Very concise responses (1-2 sentences)
- No markdown, lists, or tables
- Natural spoken language
- Arabic-first when user speaks Arabic
- Step limits when instructions are needed
"""

from __future__ import annotations

from pathlib import Path

from .tenant import TenantContext

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_voice_prompt(persona: str, tenant: TenantContext | None = None) -> str:
    """Load a voice-optimized system prompt for the given persona.

    Args:
        persona: One of the prompt file names without extension,
                 e.g. "citizen-support", "merchant-assistant", etc.
        tenant: Optional tenant context for tenant-scoped customizations.

    Returns:
        The system prompt string with voice mode constraints appended.
    """
    prompt_file = _PROMPTS_DIR / f"{persona}.system.md"
    if prompt_file.exists():
        base = prompt_file.read_text(encoding="utf-8")
    else:
        base = (
            "You are Dakkah, the CityOS voice assistant. Help users with city services."
        )

    voice_constraints = (
        "\n\n## Voice Mode Constraints\n"
        "- Keep responses VERY concise (1-2 sentences maximum)\n"
        "- Do not use lists, tables, or markdown formatting\n"
        "- Speak naturally; avoid abbreviations and special characters\n"
        "- If the user speaks Arabic, respond in Arabic\n"
        "- If you need to give steps, limit to 3 steps max and speak them slowly\n"
    )

    # Tenant-specific customization
    tenant_suffix = ""
    if tenant and tenant.node_path:
        tenant_suffix = (
            f"\n\n## Tenant Context\n"
            f"- You are serving tenant: {tenant.tenant_id}\n"
            f"- Node path: {tenant.node_path}\n"
            f"- Only provide information relevant to this tenant's scope\n"
        )

    return base + voice_constraints + tenant_suffix
