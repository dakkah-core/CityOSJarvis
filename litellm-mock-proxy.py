"""
Minimal LiteLLM-compatible proxy for local E2E testing.
Uses litellm's Python SDK to route requests to providers.
No Prisma database required.
"""

import os
import sys
import json
import asyncio
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import litellm

# ---------------------------------------------------------------------------
# Provider configs (read from env)
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
MOONSHOT_API_KEY = os.environ.get("MOONSHOT_API_KEY", "")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY", "")

MODELS = [
    {"id": "gpt-4o", "object": "model", "owned_by": "openai"},
    {"id": "gpt-4o-mini", "object": "model", "owned_by": "openai"},
    {"id": "claude-sonnet-4", "object": "model", "owned_by": "anthropic"},
    {"id": "claude-haiku", "object": "model", "owned_by": "anthropic"},
    {"id": "azure-gpt-4o", "object": "model", "owned_by": "azure"},
    {"id": "gemini-pro", "object": "model", "owned_by": "google"},
    {"id": "kimi-k2", "object": "model", "owned_by": "moonshot"},
    {"id": "kimi-lite", "object": "model", "owned_by": "moonshot"},
    {"id": "llama-local", "object": "model", "owned_by": "ollama"},
    {"id": "embed-local", "object": "model", "owned_by": "ollama"},
]


def _resolve_model(model_name: str) -> tuple[str, dict]:
    """Map LiteLLM model alias to provider model."""
    mapping = {
        "gpt-4o": ("openai/gpt-4o", {"api_key": OPENAI_API_KEY}),
        "gpt-4o-mini": ("openai/gpt-4o-mini", {"api_key": OPENAI_API_KEY}),
        "claude-sonnet-4": ("anthropic/claude-sonnet-4-20250514", {"api_key": os.environ.get("ANTHROPIC_API_KEY", "")}),
        "claude-haiku": ("anthropic/claude-3-5-haiku-20241022", {"api_key": os.environ.get("ANTHROPIC_API_KEY", "")}),
        "azure-gpt-4o": ("azure/gpt-4o", {"api_base": os.environ.get("AZURE_OPENAI_ENDPOINT", ""), "api_key": os.environ.get("AZURE_OPENAI_KEY", "")}),
        "gemini-pro": ("gemini/gemini-2.5-pro-preview-03-25", {"api_key": os.environ.get("GEMINI_API_KEY", "")}),
        "kimi-k2": ("moonshot/kimi-k2-0711-preview", {"api_key": MOONSHOT_API_KEY, "api_base": "https://api.moonshot.cn/v1"}),
        "kimi-lite": ("moonshot/moonshot-v1-8k", {"api_key": MOONSHOT_API_KEY, "api_base": "https://api.moonshot.cn/v1"}),
        "llama-local": ("ollama/qwen2.5-coder:14b", {"api_base": OLLAMA_HOST}),
        "embed-local": ("ollama/qwen2.5-coder:14b", {"api_base": OLLAMA_HOST}),
    }
    if model_name not in mapping:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    return mapping[model_name]


app = FastAPI(title="LiteLLM Mock Proxy")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path in ("/health/liveliness", "/health/readiness"):
        return await call_next(request)
    auth = request.headers.get("authorization", "")
    if MASTER_KEY and not auth.endswith(MASTER_KEY):
        return JSONResponse(status_code=401, content={"error": "Invalid master key"})
    return await call_next(request)


@app.get("/health/liveliness")
async def health():
    return {"status": "healthy"}


@app.get("/v1/models")
async def list_models():
    return {"object": "list", "data": MODELS}


@app.post("/v1/chat/completions")
async def chat_completion(request: Request):
    body = await request.json()
    model_alias = body.get("model", "gpt-4o-mini")

    try:
        model, kwargs = _resolve_model(model_alias)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    messages = body.get("messages", [])
    stream = body.get("stream", False)
    max_tokens = body.get("max_tokens", 256)
    temperature = body.get("temperature", 0.7)

    if stream:
        async def _stream() -> AsyncGenerator[str, None]:
            try:
                response = await litellm.acompletion(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True,
                    **kwargs,
                )
                async for chunk in response:
                    yield f"data: {json.dumps(chunk.model_dump())}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(_stream(), media_type="text/event-stream")
    else:
        try:
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False,
                **kwargs,
            )
            return JSONResponse(content=response.model_dump())
        except litellm.RateLimitError as e:
            raise HTTPException(status_code=429, detail=str(e))
        except litellm.AuthenticationError as e:
            raise HTTPException(status_code=401, detail=str(e))
        except litellm.BadRequestError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/embeddings")
async def embeddings(request: Request):
    body = await request.json()
    model_alias = body.get("model", "embed-local")
    input_text = body.get("input", "")

    try:
        model, kwargs = _resolve_model(model_alias)
    except HTTPException:
        raise

    try:
        response = await litellm.aembedding(
            model=model,
            input=input_text,
            **kwargs,
        )
        return JSONResponse(content=response.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4000)
