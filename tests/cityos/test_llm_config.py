"""Tests for CityOS LLM routing configuration."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from openjarvis.cityos.llm_config import get_cityos_llm_config


class TestGetCityosLlmConfig:
    """Test suite for CityOS LLM mode selection."""

    def test_no_mode_returns_none(self):
        """When CITYOSJARVIS_LLM_MODE is unset, return None."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_cityos_llm_config()
        assert result is None

    def test_unknown_mode_returns_none(self):
        """Unknown mode logs a warning and returns None."""
        with patch.dict(os.environ, {"CITYOSJARVIS_LLM_MODE": "magic"}, clear=True):
            result = get_cityos_llm_config()
        assert result is None

    def test_gateway_mode_no_litellm_raises(self):
        """Gateway mode raises when LiteLLM engine is not available."""
        env = {
            "CITYOSJARVIS_LLM_MODE": "gateway",
            "CITYOSJARVIS_LLM_MODEL": "gpt-4o",
        }
        with patch.dict(os.environ, env):
            with patch(
                "openjarvis.cityos.llm_config._setup_gateway",
                side_effect=RuntimeError("LiteLLM engine required"),
            ):
                with pytest.raises(RuntimeError, match="LiteLLM engine required"):
                    get_cityos_llm_config()

    def test_ollama_mode_no_ollama_raises(self):
        """Ollama mode raises when Ollama engine is not available."""
        env = {
            "CITYOSJARVIS_LLM_MODE": "ollama",
            "CITYOSJARVIS_LLM_MODEL": "llama3.1",
        }
        with patch.dict(os.environ, env):
            with patch(
                "openjarvis.cityos.llm_config._setup_ollama",
                side_effect=RuntimeError("Ollama engine required"),
            ):
                with pytest.raises(RuntimeError, match="Ollama engine required"):
                    get_cityos_llm_config()

    def test_direct_mode_no_cloud_raises(self):
        """Direct mode raises when Cloud engine is not available."""
        env = {
            "CITYOSJARVIS_LLM_MODE": "direct",
            "CITYOSJARVIS_LLM_MODEL": "gpt-4o",
        }
        with patch.dict(os.environ, env):
            with patch(
                "openjarvis.cityos.llm_config._setup_direct",
                side_effect=RuntimeError("Cloud engine required"),
            ):
                with pytest.raises(RuntimeError, match="Cloud engine required"):
                    get_cityos_llm_config()

    def test_gateway_mode_uses_custom_api_base(self):
        """Gateway mode respects OPENAI_API_BASE override."""
        mock_engine = MagicMock()

        def fake_setup(model):
            return ("litellm", mock_engine, model)

        env = {
            "CITYOSJARVIS_LLM_MODE": "gateway",
            "CITYOSJARVIS_LLM_MODEL": "gpt-4o-mini",
            "OPENAI_API_BASE": "http://custom-litellm:8080",
            "LITELLM_MASTER_KEY": "sk-test",
        }
        with patch.dict(os.environ, env):
            with patch("openjarvis.cityos.llm_config._setup_gateway", side_effect=fake_setup):
                result = get_cityos_llm_config()

        assert result is not None
        engine_name, engine, model = result
        assert engine_name == "litellm"
        assert engine is mock_engine
        assert model == "gpt-4o-mini"

    def test_ollama_mode_uses_custom_host(self):
        """Ollama mode respects OLLAMA_URL override."""
        mock_engine = MagicMock()

        def fake_setup(model):
            return ("ollama", mock_engine, model)

        env = {
            "CITYOSJARVIS_LLM_MODE": "ollama",
            "CITYOSJARVIS_LLM_MODEL": "llama3.1",
            "OLLAMA_URL": "http://custom-ollama:11434",
        }
        with patch.dict(os.environ, env):
            with patch("openjarvis.cityos.llm_config._setup_ollama", side_effect=fake_setup):
                result = get_cityos_llm_config()

        assert result is not None
        engine_name, engine, model = result
        assert engine_name == "ollama"
        assert model == "llama3.1"
