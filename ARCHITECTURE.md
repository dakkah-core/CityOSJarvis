# CityOSJarvis Architecture

> System architecture, data flow, and component reference for CityOSJarvis.

---

## Table of Contents

1. [Overview](#overview)
2. [Component Diagram](#component-diagram)
3. [Request Flow](#request-flow)
4. [CityOS Integration Layer](#cityos-integration-layer)
5. [AI Stack](#ai-stack)
6. [Security & Compliance](#security--compliance)
7. [Observability](#observability)
8. [Client Apps](#client-apps)
9. [Deployment Patterns](#deployment-patterns)

---

## Overview

CityOSJarvis is an AI assistant runtime built on OpenJarvis, hardened for the CityOS multi-tenant smart city platform. It adds:

- **Tenant isolation** — Hierarchical Node path validation
- **Compliance gating** — PHI/PII blocking with Saudi-specific patterns
- **Audit logging** — Append-only JSONL with Loki forwarding
- **Keycloak auth** — OIDC/JWT middleware with RBAC
- **Multi-provider LLM routing** — LiteLLM proxy with fallback

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Client Layer                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   Web App    │  │   Desktop    │  │    Mobile    │  │   Voice/Kiosk   │  │
│  │  (Next.js)   │  │   (Tauri)    │  │   (Expo)     │  │                 │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────────┬────────┘  │
└─────────┼─────────────────┼─────────────────┼───────────────────┼───────────┘
          │                 │                 │                   │
          └─────────────────┴────────┬────────┴───────────────────┘
                                     │
                         ┌───────────▼───────────┐
                         │   BFF Gateway         │
                         │   /api/bff/ai/*       │
                         │   (Next.js App Router)│
                         └───────────┬───────────┘
                                     │
                         ┌───────────▼───────────┐
                         │  CityOSJarvis         │
                         │  FastAPI :8000        │
                         │                       │
│  ┌───────────────────┐│  ┌─────────────────┐  │
│  │ Auth Middleware   ││  │ Compliance Gate │  │
│  │ (Keycloak JWT)    ││  │ (PHI/PII block) │  │
│  └───────────────────┘│  └─────────────────┘  │
│  ┌───────────────────┐│  ┌─────────────────┐  │
│  │ Tenant Context    ││  │ Audit Logger    │  │
│  │ (Node hierarchy)  ││  │ (JSONL + Loki)  │  │
│  └───────────────────┘│  └─────────────────┘  │
│  ┌───────────────────┐│  ┌─────────────────┐  │
│  │ Voice Service     ││  │ MCP Tools       │  │
│  │ (STT + TTS)       ││  │ (6 domains)     │  │
│  └───────────────────┘│  └─────────────────┘  │
└───────────────────────┘└─────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI Infrastructure                               │
│  ┌────────────────────┐      ┌────────────────────┐      ┌──────────────┐   │
│  │   LiteLLM Proxy    │      │   Ollama (local)   │      │   External   │   │
│  │   :4000            │◄────►│   :11434           │      │   APIs       │   │
│  │                    │      │                    │      │   (direct)   │   │
│  │  OpenAI            │      │  llama3.1          │      │              │   │
│  │  Anthropic         │      │  nomic-embed       │      │              │   │
│  │  Azure             │      │                    │      │              │   │
│  │  Gemini            │      │                    │      │              │   │
│  │  Kimi (Moonshot)   │      │                    │      │              │   │
│  └────────────────────┘      └────────────────────┘      └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Request Flow

### Chat Completion (Streaming)

```
1. User sends POST /api/bff/ai/chat/stream
   └─► BFF Gateway validates JWT (Keycloak)
   └─► BFF injects X-Correlation-Id, X-CityOS-Tenant-Id, X-CityOS-Node-Path

2. BFF proxies to CityOSJarvis /v1/chat/completions
   └─► Auth Middleware validates Bearer token
   └─► Tenant Context extracts Node path from headers
   └─► Compliance Gate scans last user message for PHI/PII
       └─► BLOCKED → returns 400 with redacted payload
       └─► ALLOWED → continues

3. CityOSJarvis routes to LLM based on CITYOSJARVIS_LLM_MODE
   └─► gateway → LiteLLM proxy :4000
   └─► ollama  → Ollama :11434
   └─► direct  → Cloud API

4. LiteLLM selects provider based on model name
   └─► Fallback chain activates if primary provider fails
   └─► Response streamed back as SSE

5. Audit Logger writes event to /var/log/cityosjarvis/audit.jsonl
   └─► Promtail forwards to Loki
   └─► Metrics recorded (latency, tokens, tenant)
```

---

## CityOS Integration Layer

### Files

| File | Purpose |
|------|---------|
| `cityos/auth.py` | Keycloak OIDC/JWT middleware + legacy API key fallback |
| `cityos/tenant.py` | Tenant context with Node hierarchy validation |
| `cityos/compliance.py` | PHI/PII gate with Saudi-specific patterns |
| `cityos/audit.py` | Append-only JSONL audit logger |
| `cityos/loki_handler.py` | Grafana Loki log forwarding |
| `cityos/metrics.py` | Prometheus metrics middleware |
| `cityos/voice_service.py` | STT (Whisper) + TTS (Cartesia) endpoints |
| `cityos/llm_config.py` | LLM routing: gateway / ollama / direct |

### Tenant Context

```python
TenantContext(
    tenant_id="dakkah",
    node_path="global/sa/riyadh/dakkah/zone-1",
    realm_roles=["city_admin", "ai_user"],
    user_sub="uuid",
)
```

Node path pattern: `^global(/[a-z0-9-]+){0,6}$`

### Compliance Patterns

- Saudi ID / Iqama (3 formats)
- Saudi IBAN (`SA[0-9]{20,24}`)
- Saudi mobile (`+966`, `05`, `00966`)
- Credit card, email, API key, JWT
- Arabic health keywords

---

## AI Stack

### LLM Routing Modes

| Mode | Config | Endpoint | Fallback |
|------|--------|----------|----------|
| `gateway` | `CITYOSJARVIS_LLM_MODE=gateway` | LiteLLM :4000 | ✅ Multi-provider |
| `ollama` | `CITYOSJARVIS_LLM_MODE=ollama` | Ollama :11434 | ❌ Single node |
| `direct` | `CITYOSJARVIS_LLM_MODE=direct` | Cloud API | ❌ Single provider |

### LiteLLM Provider Configuration

```yaml
# infra/litellm/config.yaml
model_list:
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY

  - model_name: kimi-k2
    litellm_params:
      model: moonshot/kimi-k2-0711-preview
      api_key: os.environ/MOONSHOT_API_KEY
      api_base: https://api.moonshot.cn/v1

router_settings:
  fallback:
    - gpt-4o:
        - claude-sonnet-4
        - azure-gpt-4o
        - kimi-k2
        - llama-local
```

---

## Security & Compliance

### Authentication Flow

```
Client → Keycloak (OIDC) → JWT Token
   │
   ▼
BFF Gateway → validates JWT → forwards to Jarvis
   │
   ▼
Jarvis Auth Middleware → JWKS verify → extract roles
   │
   ▼
RBAC Check → requiredRoles: [ai_user, cityos_admin, super_admin]
```

### Data Protection

- **PII/PHI**: Blocked at compliance gate before reaching LLM
- **Audit logs**: Sanitized (content fields → `[REDACTED:Nchars]`)
- **Tenant isolation**: Storage keys prefixed with safe tenant ID
- **Secrets**: Never logged; env vars only

---

## Observability

### Metrics (Prometheus)

| Metric | Type | Labels |
|--------|------|--------|
| `cityosjarvis_requests_total` | Counter | method, endpoint, status |
| `cityosjarvis_request_duration_seconds` | Histogram | method, endpoint |
| `cityosjarvis_llm_tokens_total` | Counter | model, provider, tenant |
| `cityosjarvis_compliance_blocks_total` | Counter | category, tenant |

### Logs (Loki)

```json
{
  "timestamp": "2026-05-29T16:00:00Z",
  "event": "chat.completion",
  "actor": {"tenant_id": "dakkah", "user_sub": "uuid", "roles": ["ai_user"]},
  "request": {"model": "gpt-4o-mini", "messages_count": 3},
  "response": {"status": 200, "tokens_used": 150},
  "tools_called": [],
  "latency_ms": 450,
  "compliance": {"gate_passed": true},
  "correlation_id": "e2e-test-123"
}
```

---

## Client Apps

| App | Stack | Path | Status |
|-----|-------|------|--------|
| Web Platform | Next.js 15 | `apps/web-platform/` | ✅ Integrated |
| Desktop | Tauri v2 | `apps/cityos-jarvis-desktop/` | ✅ Scaffolded |
| Mobile Citizen | Expo SDK 55 | `apps/mobile/` | ✅ Scaffolded |
| Mobile Inspector | Expo SDK 55 | `apps/mobile-inspector/` | ✅ Scaffolded |
| Mobile Driver | Expo SDK 55 | `apps/mobile-driver/` | ✅ Scaffolded |

All clients consume the BFF gateway at `/api/bff/ai/*`.

---

## Deployment Patterns

### Pattern 1: Local Dev (External APIs)

```bash
docker compose -f deploy/docker/docker-compose.build.yml up -d
# Uses LiteLLM gateway with OpenAI/Anthropic/Kimi keys
```

### Pattern 2: Local Dev (Offline)

```bash
docker compose -f deploy/docker/docker-compose.build.yml up -d cityosjarvis ollama postgres redis
# Uses Ollama with llama3.1 — no API keys needed
```

### Pattern 3: VPS Production

```bash
cd /opt/dakkah-cityos-cms-src
docker compose -p cityos-helpers \
  -f deploy/docker-compose.helpers.yml \
  --profile ops \
  --env-file /opt/dakkah-cityos-platform/.env \
  run --rm --no-deps cityos-ops-helper jarvis-deploy "${CITYOSJARVIS_REF:-cityos/main}"
# LiteLLM gateway with multi-provider fallback
```

CMS source lives at `/opt/dakkah-cityos-cms-src`; Jarvis source lives at `/opt/dakkah-cityosjarvis-src` and is prepared by the CMS ops-helper before image build.

### Pattern 4: VPS + GPU Node

```bash
# GPU node runs Ollama
# VPS runs CityOSJarvis + LiteLLM pointing to GPU node
export OLLAMA_URL=http://gpu-node:11434
```

---

*Last updated: 2026-05-29*
