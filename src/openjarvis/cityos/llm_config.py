"""CityOS LLM routing configuration.

Selects the appropriate inference engine based on ``CITYOSJARVIS_LLM_MODE``:
  * ``gateway`` → LiteLLM proxy at http://litellm:4000 (multi-provider + fallback)
  * ``ollama``  → Direct Ollama at OLLAMA_URL (local inference)
  * ``direct``  → Cloud provider APIs directly (OpenAI, Anthropic, etc.)

This module is called from ``cli/serve.py`` before default engine discovery,
allowing CityOS deployments to override OpenJarvis's auto-discovery without
modifying upstream config.toml files.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Tuple

from openjarvis.core.registry import EngineRegistry
from openjarvis.engine._base import InferenceEngine

logger = logging.getLogger(__name__)

# Default endpoints inside the CityOS Docker network
_DEFAULT_LITELLM_URL = "http://litellm:4000"
_DEFAULT_OLLAMA_URL = "http://ollama:11434"


def get_cityos_llm_config() -> Tuple[str, InferenceEngine, str] | None:
    """Return (engine_name, engine, model_name) when CityOS LLM mode is active.

    Returns ``None`` when no CityOS LLM mode is set, allowing upstream
    OpenJarvis engine discovery to proceed normally.
    """
    mode = os.environ.get("CITYOSJARVIS_LLM_MODE", "").strip().lower()
    if not mode:
        return None

    model = os.environ.get("CITYOSJARVIS_LLM_MODEL", "gpt-4o-mini")

    if mode == "gateway":
        return _setup_gateway(model)
    if mode == "ollama":
        return _setup_ollama(model)
    if mode == "direct":
        return _setup_direct(model)

    logger.warning(
        "Unknown CITYOSJARVIS_LLM_MODE=%r, falling back to default discovery", mode
    )
    return None


def _setup_gateway(model: str) -> Tuple[str, InferenceEngine, str]:
    """LiteLLM proxy mode — unified OpenAI-compatible API."""
    api_base = os.environ.get("OPENAI_API_BASE", _DEFAULT_LITELLM_URL).rstrip("/")
    master_key = os.environ.get("LITELLM_MASTER_KEY", "")

    logger.info("CityOS LLM mode=gateway → LiteLLM proxy at %s", api_base)

    # LiteLLM engine may not be registered if the SDK isn't installed
    if not EngineRegistry.contains("litellm"):
        try:
            import openjarvis.engine.litellm  # noqa: F401
        except ImportError:
            logger.error(
                "LiteLLM engine not available. Install with: uv sync "
                "--extra inference-cloud"
            )
            raise RuntimeError(
                "LiteLLM engine required for gateway mode but not installed"
            )

    cls: Any = EngineRegistry.get("litellm")
    engine = cls(api_base=api_base, default_model=model)

    # When a master key is set, inject it into the LiteLLM call kwargs
    if master_key:
        os.environ["LITELLM_API_KEY"] = master_key

    return ("litellm", engine, model)


def _setup_ollama(model: str) -> Tuple[str, InferenceEngine, str]:
    """Ollama direct mode — local inference only."""
    host = os.environ.get("OLLAMA_URL", _DEFAULT_OLLAMA_URL).rstrip("/")

    logger.info("CityOS LLM mode=ollama → Ollama at %s", host)

    if not EngineRegistry.contains("ollama"):
        try:
            import openjarvis.engine.ollama  # noqa: F401
        except ImportError:
            logger.error("Ollama engine not available.")
            raise RuntimeError("Ollama engine required but not installed")

    cls: Any = EngineRegistry.get("ollama")
    engine = cls(host=host)
    return ("ollama", engine, model)


def _setup_direct(model: str) -> Tuple[str, InferenceEngine, str]:
    """Direct cloud API mode — bypass LiteLLM, talk to provider APIs directly."""
    logger.info("CityOS LLM mode=direct → cloud APIs")

    if not EngineRegistry.contains("cloud"):
        try:
            import openjarvis.engine.cloud  # noqa: F401
        except ImportError:
            logger.error(
                "Cloud engine not available. Install with: uv sync "
                "--extra inference-cloud"
            )
            raise RuntimeError(
                "Cloud engine required for direct mode but not installed"
            )

    cls: Any = EngineRegistry.get("cloud")
    engine = cls()
    return ("cloud", engine, model)
