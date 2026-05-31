"""CityOS Voice Service — Python backend for voice assistant.

This module runs inside CityOSJarvis and handles:
- Intent-to-query translation (structured voice intents → natural language)
- Agent routing via the existing OpenJarvis orchestrator
- SSML + plain text response generation
- Optional TTS (Cartesia) when ENABLE_TTS=true
- STT endpoint (faster-whisper) for direct audio ingestion
- Compliance gating and audit logging

Why Python instead of TypeScript/Express?
- faster-whisper (STT) is a Python package
- TTS engines (Cartesia, Coqui, Piper) are Python-native
- Direct in-process access to OpenJarvis agent runtime
- Audio processing (librosa, pydub) is Python-native
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from openjarvis.agents._stubs import AgentContext
from openjarvis.core.types import Message, Role

from .tenant import TenantContext, get_tenant_context
from .compliance import ComplianceGate
from .audit import CityOSAuditLogger
from . import metrics as jarvis_metrics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/voice", tags=["voice"])

# Lazy-loaded STT model
_stt_model: Any | None = None

# Lazy-loaded TTS backend
_tts_backend: Any | None = None

ENABLE_TTS = os.environ.get("ENABLE_TTS", "false").lower() in ("true", "1", "yes")


def _get_stt_model() -> Any:
    """Lazy-load faster-whisper model."""
    global _stt_model
    if _stt_model is None:
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-untyped]

            model_size = os.environ.get("WHISPER_MODEL", "base")
            device = "cuda" if os.environ.get("CUDA_VISIBLE_DEVICES") else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            _stt_model = WhisperModel(
                model_size, device=device, compute_type=compute_type
            )
            logger.info(
                "Loaded faster-whisper model: %s on %s", model_size, device
            )
        except ImportError:
            logger.error(
                "faster-whisper not installed. "
                "Install with: uv sync --extra speech"
            )
            raise
    return _stt_model


def _get_tts_backend() -> Any:
    """Lazy-load TTS backend (Cartesia)."""
    global _tts_backend
    if _tts_backend is None and ENABLE_TTS:
        try:
            from openjarvis.speech.cartesia_tts import CartesiaTTSBackend
            _tts_backend = CartesiaTTSBackend()
            logger.info("Loaded Cartesia TTS backend")
        except Exception as e:
            logger.error("Failed to load TTS backend: %s", e)
            _tts_backend = None
    return _tts_backend


def _build_ssml(text: str, pause_ms: int = 400) -> str:
    """Wrap plain text in SSML with natural pauses after sentences."""
    # Add pauses after sentence terminators
    text = re.sub(
        r"([.!?])(\s+)",
        rf"\1 <break time='{pause_ms}ms'/> ",
        text,
    )
    # Normalize multiple spaces
    text = re.sub(r"\s+", " ", text)
    return f"<speak>{text.strip()}</speak>"


def _detect_language(text: str) -> str:
    """Detect if text is primarily Arabic or English."""
    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    total_chars = len(text.strip())
    if total_chars == 0:
        return "en"
    return "ar" if arabic_chars / total_chars > 0.3 else "en"


def _intent_to_query(intent: str, params: dict[str, Any]) -> str:
    """Convert structured voice intent to natural language for the agent."""
    intent_map: dict[str, str] = {
        "city.services.list": "What city services are available?",
        "permit.status.check": f"What is the status of permit {params.get('permit_id', '')}?",
        "prayer.times.today": "What are the prayer times today?",
        "traffic.report": "Report a traffic issue",
        "waste.schedule": "When is waste collection?",
        "emergency.contact": "I need emergency services",
        "weather.today": "What is the weather today?",
        "news.city": "What is the latest city news?",
    }

    if intent in intent_map:
        return intent_map[intent]

    # Fallback: use parameters to construct query
    param_str = ", ".join(f"{k}={v}" for k, v in params.items())
    return f"Intent: {intent}. Parameters: {param_str}."


def _should_end_session(intent: str) -> bool:
    """Determine if the voice session should end after this response."""
    end_session_intents = {
        "goodbye",
        "thank.you",
        "cancel",
        "stop",
        "prayer.times.today",
        "weather.today",
    }
    return intent.split(".")[-1] in end_session_intents


def _generate_suggestions(intent: str, _response_text: str) -> list[str]:
    """Generate follow-up suggestion chips based on context."""
    suggestions: dict[str, list[str]] = {
        "city.services.list": [
            "Water connection",
            "Road maintenance",
            "Waste collection",
            "Building permits",
        ],
        "permit.status.check": [
            "Apply for permit",
            "Required documents",
            "Contact zoning",
        ],
        "prayer.times.today": [
            "Weather today",
            "Mosques nearby",
            "Ramadan schedule",
        ],
        "waste.schedule": [
            "Recycling info",
            "Report missed pickup",
            "Bulk waste disposal",
        ],
        "traffic.report": [
            "Report accident",
            "Road closures",
            "Public transport",
        ],
    }
    return suggestions.get(intent, ["Help", "Start over"])


def _load_voice_system_prompt(tenant: TenantContext | None) -> str:
    """Load the CityOS voice-optimized system prompt."""
    from .voice_prompts import load_voice_prompt
    return load_voice_prompt("citizen-support", tenant=tenant)


def _run_agent_sync(
    agent: Any,
    query: str,
    system_prompt: str,
    tenant: TenantContext | None = None,
) -> dict[str, Any]:
    """Run the agent synchronously with tenant isolation (called in thread pool)."""
    from .tenant_runtime import TenantAwareAgentRunner
    runner = TenantAwareAgentRunner(agent, tenant)
    return runner.run(query, system_prompt)


def _synthesize_if_enabled(text: str, lang: str) -> dict[str, str] | None:
    """Synthesize audio if TTS is enabled. Returns audio metadata or None."""
    if not ENABLE_TTS:
        return None
    backend = _get_tts_backend()
    if backend is None:
        return None
    try:
        result = backend.synthesize(
            text,
            language=lang,
            output_format="mp3",
        )
        audio_b64 = base64.b64encode(result.audio).decode("utf-8")
        return {
            "audioBase64": audio_b64,
            "audioFormat": result.format,
            "voiceId": result.voice_id,
        }
    except Exception as e:
        logger.warning("TTS synthesis failed: %s", e)
        return None


@router.post("/process-intent")
async def process_intent(
    request: Request,
    body: dict[str, Any],
) -> JSONResponse:
    """Process a voice intent and return SSML + plain text + optional audio."""
    tenant = get_tenant_context(request)
    audit = CityOSAuditLogger()
    gate = ComplianceGate()

    intent = body.get("intent", "")
    params = body.get("parameters", {})
    session_id = body.get("sessionId", "")
    generate_audio = body.get("generateAudio", False)
    tenant_id = tenant.tenant_id if tenant else "default"

    start_time = time.perf_counter()

    # Build natural language query from intent + params
    user_query = _intent_to_query(intent, params)

    # Try Arabic parser first
    from .voice_arabic import parse_arabic_intent
    ar_result = parse_arabic_intent(user_query)
    if ar_result and ar_result.confidence > 0.6:
        intent = ar_result.intent
        user_query = ar_result.normalized_text
        if ar_result.entities:
            params.update(ar_result.entities)

    # Compliance check
    classification = gate.classify(user_query)
    if not classification.allowed:
        latency = time.perf_counter() - start_time
        latency_ms = latency * 1000
        lang = ar_result.language if ar_result else "en"
        jarvis_metrics.VOICE_QUERIES.labels(
            tenant_id=tenant_id, language=lang, intent=intent
        ).inc()
        jarvis_metrics.VOICE_DURATION.labels(
            tenant_id=tenant_id, language=lang
        ).observe(latency)
        jarvis_metrics.VOICE_CONFIDENCE.labels(
            tenant_id=tenant_id, language=lang
        ).observe(0.0)
        audit.log(
            event="voice.intent.blocked",
            tenant=tenant,
            request={"intent": intent, "params": params, "session_id": session_id},
            response={"status": "blocked", "reason": classification.reason},
            compliance={
                "category": classification.category,
                "gate_passed": False,
            },
            latency_ms=latency_ms,
        )
        safe_msg = (
            classification.reason
            or "Request blocked for privacy. Please contact your service center."
        )
        response_payload: dict[str, Any] = {
            "ssml": _build_ssml(safe_msg),
            "plainText": safe_msg,
            "shouldEndSession": True,
            "suggestions": [],
        }
        if generate_audio and ENABLE_TTS:
            audio_meta = _synthesize_if_enabled(safe_msg, _detect_language(safe_msg))
            if audio_meta:
                response_payload.update(audio_meta)
        return JSONResponse(response_payload)

    # Route to agent
    try:
        agent = getattr(request.app.state, "agent", None)
        if agent is None:
            logger.error("No agent configured on app.state")
            raise HTTPException(status_code=503, detail="AI agent not available")

        system_prompt = _load_voice_system_prompt(tenant)

        # Run agent in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        agent_result = await loop.run_in_executor(
            None, _run_agent_sync, agent, user_query, system_prompt, tenant
        )

        response_text = agent_result["content"]
        lang = ar_result.language if ar_result else _detect_language(response_text)
        ssml = _build_ssml(response_text)

        latency = time.perf_counter() - start_time
        latency_ms = latency * 1000

        jarvis_metrics.VOICE_QUERIES.labels(
            tenant_id=tenant_id, language=lang, intent=intent
        ).inc()
        jarvis_metrics.VOICE_DURATION.labels(
            tenant_id=tenant_id, language=lang
        ).observe(latency)
        jarvis_metrics.VOICE_CONFIDENCE.labels(
            tenant_id=tenant_id, language=lang
        ).observe(ar_result.confidence if ar_result else 0.8)

        audit.log(
            event="voice.intent.success",
            tenant=tenant,
            request={"intent": intent, "params": params, "session_id": session_id},
            response={"status": "success", "language": lang},
            tools_called=[tr["name"] for tr in agent_result.get("tool_results", [])],
            compliance={"category": classification.category, "gate_passed": True},
            latency_ms=latency_ms,
        )

        response_payload = {
            "ssml": ssml,
            "plainText": response_text,
            "shouldEndSession": _should_end_session(intent),
            "suggestions": _generate_suggestions(intent, response_text),
            "language": lang,
        }

        if generate_audio and ENABLE_TTS:
            audio_meta = _synthesize_if_enabled(response_text, lang)
            if audio_meta:
                response_payload.update(audio_meta)
                audit.log(
                    event="voice.tts.generated",
                    tenant=tenant,
                    request={"text_length": len(response_text), "language": lang},
                    response={"format": audio_meta.get("audioFormat")},
                )

        return JSONResponse(response_payload)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Voice intent processing failed")
        latency = time.perf_counter() - start_time
        latency_ms = latency * 1000
        lang = ar_result.language if ar_result else "en"
        jarvis_metrics.VOICE_QUERIES.labels(
            tenant_id=tenant_id, language=lang, intent="error"
        ).inc()
        audit.log(
            event="voice.intent.error",
            tenant=tenant,
            request={"intent": intent, "params": params, "session_id": session_id},
            response={"status": "error", "error": str(e)},
            latency_ms=latency_ms,
        )
        raise HTTPException(
            status_code=500, detail="Voice processing failed"
        ) from e


@router.post("/speak")
async def speak(
    request: Request,
    body: dict[str, Any],
) -> JSONResponse:
    """Direct TTS endpoint — synthesize text to speech audio.

    Request body:
        text: str          -- text to synthesize
        language: str      -- "en" or "ar" (optional, auto-detected)
        voiceId: str       -- Cartesia voice ID (optional)
        outputFormat: str  -- "mp3" or "pcm_f32le" (default: mp3)
    """
    if not ENABLE_TTS:
        raise HTTPException(status_code=503, detail="TTS is not enabled. Set ENABLE_TTS=true")

    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Missing text field")

    lang = body.get("language") or _detect_language(text)
    voice_id = body.get("voiceId", "")
    output_format = body.get("outputFormat", "mp3")

    backend = _get_tts_backend()
    if backend is None:
        raise HTTPException(status_code=503, detail="TTS backend unavailable")

    try:
        result = backend.synthesize(
            text,
            language=lang,
            voice_id=voice_id,
            output_format=output_format,
        )
        audio_b64 = base64.b64encode(result.audio).decode("utf-8")
        return JSONResponse({
            "audioBase64": audio_b64,
            "audioFormat": result.format,
            "voiceId": result.voice_id,
            "language": lang,
            "durationEstimate": len(text.split()) * 0.4,  # rough heuristic
        })
    except Exception as e:
        logger.exception("TTS synthesis failed")
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}") from e


@router.post("/process-call")
async def process_call(
    request: Request,
    body: dict[str, Any],
) -> JSONResponse:
    """Process a phone call voice request (Twilio-style)."""
    speech_text = body.get("speechText", "")
    call_id = body.get("callId", "")

    # Run through the same pipeline with a voice-call intent
    return await process_intent(
        request,
        {
            "intent": "voice.call",
            "parameters": {"query": speech_text, "callId": call_id},
            "sessionId": call_id,
        },
    )


@router.post("/stt")
async def speech_to_text(
    request: Request,
    body: dict[str, Any],
) -> JSONResponse:
    """Convert audio (base64 WAV) to text using faster-whisper."""
    audio_b64 = body.get("audio", "")
    language = body.get("language", "ar")

    if not audio_b64:
        raise HTTPException(status_code=400, detail="Missing audio data")

    try:
        audio_bytes = base64.b64decode(audio_b64)
        model = _get_stt_model()

        # Write to temp file (faster-whisper needs file path)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        segments, info = model.transcribe(
            temp_path, language=language, beam_size=5
        )
        text = " ".join([segment.text for segment in segments])

        os.unlink(temp_path)

        return JSONResponse(
            {
                "text": text,
                "language": info.language,
                "probability": info.language_probability,
            }
        )

    except Exception as e:
        logger.exception("STT failed")
        raise HTTPException(
            status_code=500, detail="Speech recognition failed"
        ) from e


# Re-export for app.py registration
__all__ = ["router"]
