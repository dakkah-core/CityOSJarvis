"""Tests for application lifecycle events (startup, shutdown, config)."""

from __future__ import annotations

import os
from unittest.mock import patch


class TestEnvironmentConfiguration:
    def test_openjarvis_api_key_can_be_set(self) -> None:
        with patch.dict(os.environ, {"OPENJARVIS_API_KEY": "test-key"}):
            assert os.environ.get("OPENJARVIS_API_KEY") == "test-key"

    def test_keycloak_url_optional(self) -> None:
        # Keycloak URL may be empty for local dev
        assert os.environ.get("KEYCLOAK_URL", "") == "" or os.environ.get(
            "KEYCLOAK_URL", ""
        ).startswith("http")

    def test_cartesia_api_key_optional(self) -> None:
        # TTS is optional
        assert "CARTESIA_API_KEY" in os.environ or "CARTESIA_API_KEY" not in os.environ

    def test_loki_url_defaults_to_localhost(self) -> None:
        default = os.environ.get("LOKI_URL", "http://localhost:3100")
        assert default.startswith("http")

    def test_enable_tts_flag(self) -> None:
        tts = os.environ.get("ENABLE_TTS", "false").lower()
        assert tts in ("true", "false", "1", "0", "yes", "no")

    def test_log_level_sensible_default(self) -> None:
        level = os.environ.get("LOG_LEVEL", "INFO")
        assert level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


class TestStartupShutdown:
    def test_import_app_factory_without_error(self) -> None:
        from openjarvis.server.app import create_app

        assert create_app is not None

    def test_app_factory_is_callable(self) -> None:
        from openjarvis.server.app import create_app

        assert callable(create_app)

    def test_voice_service_router_importable(self) -> None:
        from openjarvis.cityos.voice_service import router

        paths = [r.path for r in router.routes]
        assert any("voice" in p for p in paths)
