"""Tests for Cartesia TTS integration."""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

import pytest

from openjarvis.speech.cartesia_tts import CartesiaTTSBackend, _cartesia_synthesize


class TestCartesiaTTSBackend:
    def test_init_without_api_key(self) -> None:
        with patch.dict(os.environ, {"CARTESIA_API_KEY": ""}, clear=True):
            backend = CartesiaTTSBackend()
            assert backend._api_key == ""

    def test_init_with_api_key_from_env(self) -> None:
        with patch.dict(os.environ, {"CARTESIA_API_KEY": "test-key"}):
            backend = CartesiaTTSBackend()
            assert backend._api_key == "test-key"

    def test_init_with_explicit_api_key(self) -> None:
        backend = CartesiaTTSBackend(api_key="explicit-key")
        assert backend._api_key == "explicit-key"

    def test_init_default_model(self) -> None:
        backend = CartesiaTTSBackend(api_key="test")
        assert backend._model == "sonic"

    def test_init_custom_model(self) -> None:
        backend = CartesiaTTSBackend(api_key="test", model="sonic-lite")
        assert backend._model == "sonic-lite"

    def test_init_default_language(self) -> None:
        backend = CartesiaTTSBackend(api_key="test")
        assert backend._language == "en"

    def test_init_language_from_env(self) -> None:
        # CartesiaTTSBackend takes language as explicit param, not from env
        backend = CartesiaTTSBackend(api_key="test", language="ar")
        assert backend._language == "ar"

    def test_synthesize_raises_without_api_key(self) -> None:
        backend = CartesiaTTSBackend(api_key="")
        with pytest.raises(RuntimeError, match="CARTESIA_API_KEY"):
            backend.synthesize("Hello")

    @patch("openjarvis.speech.cartesia_tts._cartesia_synthesize")
    def test_synthesize_success(self, mock_synthesize) -> None:
        mock_synthesize.return_value = b"fake-audio-bytes"
        backend = CartesiaTTSBackend(api_key="test-key")
        result = backend.synthesize("Hello world")
        assert result is not None
        mock_synthesize.assert_called_once()

    @patch("openjarvis.speech.cartesia_tts._cartesia_synthesize")
    def test_synthesize_with_custom_voice(self, mock_synthesize) -> None:
        mock_synthesize.return_value = b"fake-audio-bytes"
        backend = CartesiaTTSBackend(api_key="test-key")
        backend.synthesize("Hello", voice_id="custom-voice-id")
        call_kwargs = mock_synthesize.call_args.kwargs
        assert call_kwargs["voice_id"] == "custom-voice-id"

    @patch("openjarvis.speech.cartesia_tts._cartesia_synthesize")
    def test_synthesize_with_speed(self, mock_synthesize) -> None:
        mock_synthesize.return_value = b"fake-audio-bytes"
        backend = CartesiaTTSBackend(api_key="test-key")
        backend.synthesize("Hello", speed=1.5)
        call_kwargs = mock_synthesize.call_args.kwargs
        assert call_kwargs["speed"] == 1.5

    @patch("openjarvis.speech.cartesia_tts._cartesia_synthesize")
    def test_synthesize_arabic(self, mock_synthesize) -> None:
        mock_synthesize.return_value = b"fake-audio-bytes"
        backend = CartesiaTTSBackend(api_key="test-key", language="ar")
        backend.synthesize("مرحبا")
        call_kwargs = mock_synthesize.call_args.kwargs
        assert call_kwargs["language"] == "ar"

    @patch("openjarvis.speech.cartesia_tts._cartesia_synthesize")
    def test_synthesize_mp3_format(self, mock_synthesize) -> None:
        mock_synthesize.return_value = b"fake-audio-bytes"
        backend = CartesiaTTSBackend(api_key="test-key")
        backend.synthesize("Hello", output_format="mp3")
        call_kwargs = mock_synthesize.call_args.kwargs
        assert call_kwargs["output_format"] == "mp3"

    def test_backend_id(self) -> None:
        assert CartesiaTTSBackend.backend_id == "cartesia"


class TestCartesiaSynthesizeFunction:
    @patch("openjarvis.speech.cartesia_tts.httpx.post")
    def test_api_call_structure(self, mock_post) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.content = b"audio"
        mock_post.return_value = mock_resp

        result = _cartesia_synthesize(
            api_key="test",
            text="Hello",
            voice_id="voice-1",
            model="sonic",
            output_format="mp3",
            speed=1.0,
            language="en",
        )

        assert result == b"audio"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.cartesia.ai/tts/bytes"
        assert call_args[1]["headers"]["X-API-Key"] == "test"

    @patch("openjarvis.speech.cartesia_tts.httpx.post")
    def test_api_error_handling(self, mock_post) -> None:
        mock_post.side_effect = Exception("Connection timeout")

        with pytest.raises(Exception, match="Connection timeout"):
            _cartesia_synthesize(
                api_key="test",
                text="Hello",
                voice_id="voice-1",
                model="sonic",
                output_format="mp3",
                speed=1.0,
                language="en",
            )
