# AI Stack E2E Tests

End-to-end tests for the CityOSJarvis AI infrastructure.

## Prerequisites

```bash
cd deploy/docker
docker compose -f docker-compose.build.yml up -d --build
```

Wait for all services to be healthy:
```bash
docker compose -f docker-compose.build.yml ps
```

## Run Tests

```bash
# From repo root
npx playwright test --config=e2e/ai-stack/playwright.config.ts

# With env overrides
E2E_JARVIS_URL=http://localhost:8000 \
E2E_LITELLM_URL=http://localhost:4000 \
E2E_OLLAMA_URL=http://localhost:11434 \
npx playwright test --config=e2e/ai-stack/playwright.config.ts

# Headed mode for debugging
npx playwright test --config=e2e/ai-stack/playwright.config.ts --headed
```

## Test Files

| File | Coverage |
|------|----------|
| `health-checks.spec.ts` | Jarvis, LiteLLM, Ollama health endpoints + model list |
| `gateway-routing.spec.ts` | Provider routing (OpenAI, Kimi, Ollama embeddings) |
| `jarvis-chat.spec.ts` | Streaming/non-streaming chat, compliance gate, tenant context |
| `fallback-resilience.spec.ts` | Rate limiting, missing models, LLM unavailability |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `E2E_JARVIS_URL` | `http://localhost:8000` | CityOSJarvis base URL |
| `E2E_LITELLM_URL` | `http://localhost:4000` | LiteLLM proxy base URL |
| `E2E_OLLAMA_URL` | `http://localhost:11434` | Ollama base URL |
| `LITELLM_MASTER_KEY` | `sk-litellm-cityos-local` | LiteLLM proxy auth key |
| `OPENJARVIS_API_KEY` | `cityos-local-key` | Jarvis API key |
