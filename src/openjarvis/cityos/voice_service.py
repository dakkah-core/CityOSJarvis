"""CityOS Voice Service — Python backend for voice assistant.

This module runs inside CityOSJarvis and handles:
- Intent-to-query translation (structured voice intents → natural language)
- Agent routing via the existing OpenJarvis orchestrator
- SSML + plain text response generation
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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/voice", tags=["voice"])

# Lazy-loaded STT model
_stt_model: Any | None = None


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
    prompts_dir = Path(__file__).parent / "prompts"
    prompt_file = prompts_dir / "citizen-support.system.md"

    if prompt_file.exists():
        base_prompt = prompt_file.read_text(encoding="utf-8")
    else:
        base_prompt = (
            "You are Dakkah, the CityOS voice assistant. "
            "Help users with city services."
        )

    # Append voice-specific constraints
    voice_constraints = (
        "\n\n## Voice Mode Constraints\n"
        "- Keep responses VERY concise (1-2 sentences maximum)\n"
        "- Do not use lists, tables, or markdown formatting\n"
        "- Speak naturally; avoid abbreviations and special characters\n"
        "- If the user speaks Arabic, respond in Arabic\n"
        "- If you need to give steps, limit to 3 steps max and speak them slowly\n"
    )
    return base_prompt + voice_constraints


def _run_agent_sync(
    agent: Any,
    query: str,
    system_prompt: str,
) -> dict[str, Any]:
    """Run the agent synchronously (called in thread pool)."""
    ctx = AgentContext()
    messages = [
        Message(role=Role.SYSTEM, content=system_prompt),
        Message(role=Role.USER, content=query),
    ]
    for m in messages:
        ctx.conversation.add(m)

    result = agent.run(query, context=ctx)
    return {
        "content": result.content,
        "tool_results": [
            {"name": tr.name, "status": tr.status}
            for tr in (result.tool_results or [])
        ],
        "turns": result.turns,
    }


@router.post("/process-intent")
async def process_intent(
    request: Request,
    body: dict[str, Any],
) -> JSONResponse:
    """Process a voice intent and return SSML + plain text."""
    tenant = get_tenant_context(request)
    audit = CityOSAuditLogger()
    gate = ComplianceGate()

    intent = body.get("intent", "")
    params = body.get("parameters", {})
    session_id = body.get("sessionId", "")

    start_time = time.perf_counter()

    # Build natural language query from intent + params
    user_query = _intent_to_query(intent, params)

    # Compliance check
    classification = gate.classify(user_query)
    if not classification.allowed:
        latency_ms = (time.perf_counter() - start_time) * 1000
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
        return JSONResponse(
            {
                "ssml": _build_ssml(safe_msg),
                "plainText": safe_msg,
                "shouldEndSession": True,
                "suggestions": [],
            }
        )

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
            None, _run_agent_sync, agent, user_query, system_prompt
        )

        response_text = agent_result["content"]
        lang = _detect_language(response_text)
        ssml = _build_ssml(response_text)

        latency_ms = (time.perf_counter() - start_time) * 1000

        audit.log(
            event="voice.intent.success",
            tenant=tenant,
            request={"intent": intent, "params": params, "session_id": session_id},
            response={"status": "success", "language": lang},
            tools_called=[tr["name"] for tr in agent_result.get("tool_results", [])],
            compliance={"category": classification.category, "gate_passed": True},
            latency_ms=latency_ms,
        )

        return JSONResponse(
            {
                "ssml": ssml,
                "plainText": response_text,
                "shouldEndSession": _should_end_session(intent),
                "suggestions": _generate_suggestions(intent, response_text),
                "language": lang,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Voice intent processing failed")
        latency_ms = (time.perf_counter() - start_time) * 1000
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
