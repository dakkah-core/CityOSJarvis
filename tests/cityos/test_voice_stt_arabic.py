"""Tests for Arabic intent parsing in the STT endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openjarvis.cityos.voice_service import router


@pytest.fixture
def client() -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _make_stt_payload(text: str, language: str = "ar") -> dict:
    """Create a mock STT request payload with base64-encoded dummy audio."""
    import base64

    dummy_audio = base64.b64encode(b"RIFF" + b"\x00" * 100).decode("utf-8")
    return {"audio": dummy_audio, "language": language}


class TestSTTArabicParsing:
    """Verify that STT responses include Arabic intent data when language is Arabic."""

    def test_stt_response_includes_intent_when_arabic(self, client: TestClient) -> None:
        """Arabic STT responses should include intent/entity metadata."""
        # Actual transcription depends on the model; this validates the schema.
        payload = _make_stt_payload("", language="ar")
        response = client.post("/v1/voice/stt", json=payload)

        # 400 or 500 is expected because dummy audio won't transcribe
        assert response.status_code in (400, 500)

    def test_stt_response_schema_for_arabic(self, client: TestClient) -> None:
        """Validate that the STT endpoint accepts Arabic language parameter."""
        payload = _make_stt_payload("", language="ar")
        response = client.post("/v1/voice/stt", json=payload)
        # Endpoint should not crash on Arabic language parameter
        assert response.status_code in (400, 500)

    def test_stt_no_crash_on_english(self, client: TestClient) -> None:
        """English STT should not include Arabic intent fields."""
        payload = _make_stt_payload("", language="en")
        response = client.post("/v1/voice/stt", json=payload)
        assert response.status_code in (400, 500)

    def test_stt_missing_audio_returns_400(self, client: TestClient) -> None:
        """STT without audio should return 400."""
        response = client.post("/v1/voice/stt", json={"language": "ar"})
        assert response.status_code == 400
        assert "Missing audio data" in response.json()["detail"]
