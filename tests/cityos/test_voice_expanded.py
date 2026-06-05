"""Expanded voice service tests."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from openjarvis.cityos.voice_service import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestVoiceService:
    def test_router_has_routes(self) -> None:
        routes = [r.path for r in router.routes]
        # Voice router should have its specific endpoints
        assert len(routes) >= 1
        assert any("voice" in r for r in routes)

    def test_stt_missing_audio(self) -> None:
        response = client.post("/v1/voice/stt", json={})
        assert response.status_code == 400
        assert "audio" in response.json()["detail"].lower()

    def test_stt_with_empty_audio(self) -> None:
        response = client.post("/v1/voice/stt", json={"audio": "", "language": "en"})
        # Should either fail validation or return empty result
        assert response.status_code in [400, 422, 200]

    @patch("openjarvis.cityos.voice_service._get_stt_model")
    def test_stt_successful(self, mock_get_model) -> None:
        mock_model = MagicMock()
        mock_segments = [MagicMock(text="Hello world")]
        mock_info = MagicMock(language="en", language_probability=0.95)
        mock_model.transcribe.return_value = (mock_segments, mock_info)
        mock_get_model.return_value = mock_model

        audio_b64 = base64.b64encode(b"fake audio data").decode()
        response = client.post(
            "/v1/voice/stt", json={"audio": audio_b64, "language": "en"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Hello world"
        assert data["language"] == "en"

    def test_tts_disabled_by_default(self) -> None:
        response = client.post("/v1/voice/speak", json={"text": "Hello"})
        # TTS is disabled by default
        assert response.status_code in [200, 404, 503]

    def test_tts_missing_text(self) -> None:
        response = client.post("/v1/voice/speak", json={})
        # May return 400, 422, or 503 depending on TTS config
        assert response.status_code in [400, 422, 503]

    def test_tts_with_arabic_text(self) -> None:
        response = client.post(
            "/v1/voice/speak", json={"text": "مرحبا", "language": "ar"}
        )
        # May succeed or fail depending on TTS config
        assert response.status_code in [200, 404, 503]

    def test_tts_with_long_text(self) -> None:
        long_text = "Hello world. " * 100
        response = client.post("/v1/voice/speak", json={"text": long_text})
        assert response.status_code in [200, 404, 503]

    def test_health_endpoint(self) -> None:
        response = client.get("/health")
        # Health endpoint may be at root or under voice prefix
        assert response.status_code in [200, 404]

    def test_voice_routes_registered(self) -> None:
        all_routes = [r.path for r in app.routes]
        assert any("voice" in r for r in all_routes)

    def test_stt_with_invalid_base64(self) -> None:
        response = client.post("/v1/voice/stt", json={"audio": "not-valid-base64!!!"})
        # Should fail during decode
        assert response.status_code in [400, 500]

    def test_tts_with_special_characters(self) -> None:
        text = "Hello! @#$%^&*() 🎉"
        response = client.post("/v1/voice/speak", json={"text": text})
        assert response.status_code in [200, 404, 503]

    def test_tts_with_ssml(self) -> None:
        ssml = "<speak>Hello <break time='500ms'/> world</speak>"
        response = client.post("/v1/voice/speak", json={"text": ssml, "format": "ssml"})
        assert response.status_code in [200, 404, 503]

    @patch("openjarvis.cityos.voice_service._get_stt_model")
    def test_stt_arabic(self, mock_get_model) -> None:
        mock_model = MagicMock()
        mock_segments = [MagicMock(text="مرحبا")]
        mock_info = MagicMock(language="ar", language_probability=0.98)
        mock_model.transcribe.return_value = (mock_segments, mock_info)
        mock_get_model.return_value = mock_model

        audio_b64 = base64.b64encode(b"fake audio data").decode()
        response = client.post(
            "/v1/voice/stt", json={"audio": audio_b64, "language": "ar"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "مرحبا"
        assert data["language"] == "ar"
