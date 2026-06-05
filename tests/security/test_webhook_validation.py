"""Tests for webhook fail-closed validation (Section 3)."""

from __future__ import annotations

from unittest.mock import patch

import pytest


class _Bridge:
    def handle_incoming(self, *_args, **_kwargs):
        return "ok"


class _SendBlue:
    def __init__(self, webhook_secret: str = "") -> None:
        self.webhook_secret = webhook_secret

    def send(self, *_args, **_kwargs) -> None:
        return None


def _make_client(**kwargs):
    pytest.importorskip("fastapi")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from openjarvis.server.webhook_routes import create_webhook_router

    app = FastAPI()
    app.include_router(create_webhook_router(_Bridge(), **kwargs))
    return TestClient(app)


class TestTwilioValidationFailClosed:
    """Twilio validation must reject when SDK is unavailable."""

    def test_missing_sdk_returns_false(self) -> None:
        pytest.importorskip("fastapi")
        from openjarvis.server.webhook_routes import _validate_twilio_signature

        with patch.dict(
            "sys.modules", {"twilio": None, "twilio.request_validator": None}
        ):
            result = _validate_twilio_signature(
                auth_token="test_token",
                url="https://example.com/webhooks/twilio",
                params={"Body": "hello"},
                signature="invalid",
            )
            assert result is False

    def test_empty_auth_token_returns_false(self) -> None:
        pytest.importorskip("fastapi")
        from openjarvis.server.webhook_routes import _validate_twilio_signature

        result = _validate_twilio_signature(
            auth_token="",
            url="https://example.com/webhooks/twilio",
            params={},
            signature="",
        )
        assert result is False


class TestWebhookRoutesFailClosed:
    def test_bluebubbles_rejects_when_password_missing(self) -> None:
        client = _make_client(bluebubbles_password="")

        response = client.post("/webhooks/bluebubbles", json={"type": "new-message"})

        assert response.status_code == 503

    def test_whatsapp_verify_rejects_when_token_missing(self) -> None:
        client = _make_client(whatsapp_verify_token="")

        response = client.get(
            "/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "",
                "hub.challenge": "challenge",
            },
        )

        assert response.status_code == 503

    def test_whatsapp_post_rejects_when_secret_missing(self) -> None:
        client = _make_client(whatsapp_app_secret="")

        response = client.post("/webhooks/whatsapp", json={"entry": []})

        assert response.status_code == 503

    def test_sendblue_rejects_when_secret_missing(self) -> None:
        client = _make_client(sendblue_channel=_SendBlue(webhook_secret=""))

        response = client.post(
            "/webhooks/sendblue",
            json={"from_number": "+15551234567", "content": "hello"},
        )

        assert response.status_code == 503
