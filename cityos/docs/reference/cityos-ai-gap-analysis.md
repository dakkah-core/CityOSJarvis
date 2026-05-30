---
title: CityOS AI Apps Gap Analysis and OpenJarvis Migration Strategy
description: Detailed analysis of CityOS ai-assistant and voice-assistant vs. OpenJarvis capabilities, with migration recommendations.
---

# CityOS AI Apps Gap Analysis and OpenJarvis Migration Strategy

> [← Back to CityOS Integrations](../index.md) · [← OpenJarvis Inventory](openjarvis-inventory.md)

**Date**: 2026-05-29  
**Scope**: `apps/ai-assistant/`, `apps/voice-assistant/` in CityOS vs. OpenJarvis framework  
**Authors**: CityOS Platform Engineering

---

## 1. Executive Summary

CityOS currently has two AI-related applications:

| App | Current State | Maturity | Effective Functionality |
|-----|--------------|----------|------------------------|
| `apps/ai-assistant/` | Placeholder shell | ~5% | Static "coming soon" page |
| `apps/voice-assistant/` | Basic intent handlers | ~15% | Hardcoded SSML responses, no AI model |

**There is no duplication with OpenJarvis.** CityOS apps are immature stubs; OpenJarvis is a production-ready AI framework. The correct strategy is **not** to build competing AI infrastructure in CityOS, but to **repurpose CityOS apps as thin frontends/consumers** of OpenJarvis.

**Recommended outcome**:
- `ai-assistant` → React chat UI consuming OpenJarvis `/v1/chat/completions`
- `voice-assistant` → Express webhook translating voice intents to OpenJarvis agent calls
- Both apps become **presentation layers** only; all AI logic moves to OpenJarvis

---

## 2. Current State: CityOS ai-assistant

### 2.1 File Inventory

```
apps/ai-assistant/
├── package.json              # Next.js 16.2.6, port 5012, --webpack
├── src/
│   ├── app/
│   │   ├── page.tsx          # ← "AI chat interface — coming soon" (10 lines)
│   │   ├── layout.tsx        # Basic Next.js layout
│   │   ├── globals.css       # Tailwind imports
│   │   └── *.test.tsx        # Empty tests
│   └── lib/
│       ├── env.ts            # Env validator (OPENAI_API_KEY, AI_MODEL_PROVIDER)
│       └── config/
└── e2e/smoke.spec.ts         # Empty E2E test
```

### 2.2 Code Analysis

**`src/app/page.tsx`** (entire implementation):
```tsx
export default function AiAssistantPage() {
  return (
    <main className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-3xl font-bold mb-2">CityOS AI Assistant</h1>
        <p className="text-muted-foreground">AI chat interface — coming soon</p>
      </div>
    </main>
  );
}
```

**`src/lib/env.ts`**:
- Reads `OPENAI_API_KEY`, `AI_MODEL_PROVIDER` (defaults to `'openai'`)
- Reads `BFF_API_URL`, `KEYCLOAK_URL`
- **No actual API calls are made**

### 2.3 What's Missing

| Feature | Status | Gap |
|---------|--------|-----|
| Chat UI | ❌ | No input field, no message history, no streaming |
| Model integration | ❌ | Env vars defined but unused |
| Message handling | ❌ | No state management |
| Streaming/SSE | ❌ | No real-time response handling |
| Tool calls | ❌ | No MCP or function calling |
| Memory | ❌ | No conversation persistence |
| Auth integration | ❌ | Keycloak URL in env but not wired |
| BFF integration | ❌ | BFF_API_URL in env but not used |
| Mobile responsive | ❌ | Basic centering only |
| Accessibility | ❌ | No ARIA, no focus management |
| Tests | ❌ | Empty test files |
| SDUI blocks | ❌ | No block rendering |

**Assessment**: This is a scaffolding shell with zero AI functionality. The developer created the app structure but never implemented the chat interface.

---

## 3. Current State: CityOS voice-assistant

### 3.1 File Inventory

```
apps/voice-assistant/
├── package.json              # Express + Zod, type: module
├── src/
│   ├── index.ts              # Express server bootstrap
│   ├── webhook.ts            # Webhook router
│   ├── ssml.ts               # SSML builder utility
│   ├── types.ts              # Intent type definitions
│   ├── env.ts                # PORT, NODE_ENV
│   ├── intents/
│   │   ├── registry.ts       # Intent registration system
│   │   ├── city-services.ts  # Hardcoded city service list
│   │   ├── permit-status.ts  # Hardcoded permit response
│   │   └── prayer-times.ts   # Hardcoded prayer times
│   └── lib/config/
└── dist/                     # Compiled JS output
```

### 3.2 Code Analysis

**`src/index.ts`** — Server bootstrap:
```typescript
import express from "express";
import { createWebhookRouter } from "./webhook.js";
import { registerIntent } from "./intents/registry.js";
import { cityServicesIntent } from "./intents/city-services.js";
// ... more imports

registerIntent(cityServicesIntent);
registerIntent(permitStatusIntent);
registerIntent(prayerTimesIntent);

const app = express();
app.use("/api/voice", createWebhookRouter());
app.listen(PORT);
```

**`src/intents/city-services.ts`** — Example intent (entire implementation):
```typescript
export const cityServicesIntent: IntentHandler = {
  intentName: "city.services.list",
  async handle(_params, _context): Promise<IntentResult> {
    const ssml = new SsmlBuilder()
      .say("Here are the available city services in Dakkah.")
      .pause(400)
      .say("Water connection and utilities.")
      // ... hardcoded list
      .build();

    return {
      ssml,
      plainText: "Available services: Water connection, Road maintenance...",
      shouldEndSession: false,
      card: { title: "Dakkah City Services", subtitle: "4 services available" },
      suggestions: ["Water connection", "Road maintenance", ...],
    };
  },
};
```

### 3.3 What's Missing

| Feature | Status | Gap |
|---------|--------|-----|
| Speech-to-Text | ❌ | No ASR (whisper, faster-whisper) |
| Natural language understanding | ❌ | Rule-based intent matching only |
| AI model integration | ❌ | No LLM calls whatsoever |
| Context/memory | ❌ | No session persistence |
| Dynamic responses | ❌ | All responses are hardcoded strings |
| Real data integration | ❌ | No database/API calls |
| Multi-turn conversation | ❌ | Single-shot request/response |
| Voice synthesis | ❌ | SSML generation only, no TTS engine |
| Channel integration | ❌ | No Alexa, Google Assistant, phone |
| Authentication | ❌ | No Keycloak integration |
| Tenant isolation | ❌ | No Node hierarchy awareness |
| Error handling | ❌ | Minimal try/catch |

**Assessment**: This is a basic webhook framework for voice skills with hardcoded responses. It has the **shape** of a voice assistant but contains **zero AI**. It's equivalent to an IVR (Interactive Voice Response) system from the 1990s.

---

## 4. OpenJarvis: What We Get Instead

### 4.1 Full AI Stack (No Build Required)

OpenJarvis provides everything CityOS would need to build over 12–18 months:

| Capability | OpenJarvis Status | CityOS Status |
|-----------|-------------------|---------------|
| Local LLM inference (Ollama) | ✅ Production | ❌ Not started |
| GPU inference (vLLM) | ✅ Production | ❌ Not started |
| Apple Silicon (MLX) | ✅ Production | ❌ Not started |
| Cloud fallback (OpenAI/Anthropic) | ✅ Production | ❌ Env only |
| Multi-model routing | ✅ Production | ❌ Not started |
| Streaming chat API | ✅ Production | ❌ Not started |
| 14 built-in agents | ✅ Production | ❌ Not started |
| 25+ channel integrations | ✅ Production | ❌ 0 channels |
| 30+ tools (web search, browser, code) | ✅ Production | ❌ Not started |
| MCP server/client | ✅ Production | ❌ Not started |
| Memory/index (FAISS/ColBERT) | ✅ Optional | ❌ Not started |
| Voice input (faster-whisper) | ✅ Optional | ❌ Not started |
| TTS output | ✅ Optional | ❌ SSML only |
| Trace recording | ✅ Production | ❌ Not started |
| Telemetry/observability | ✅ Production | ❌ Not started |
| Desktop app (Tauri) | ✅ Production | ❌ Not started |
| Scheduled agents | ✅ Production | ❌ Not started |
| Skill ecosystem (13,700+) | ✅ Production | ❌ Not started |
| Model fine-tuning (Pearl) | ✅ Production | ❌ Not started |
| Evaluations/benchmarks | ✅ Production | ❌ Not started |
| Rust performance extensions | ✅ Production | ❌ Not started |

### 4.2 Agent Comparison

| Agent | OpenJarvis | CityOS ai-assistant | CityOS voice-assistant |
|-------|-----------|---------------------|------------------------|
| Single-turn chat | `simple` agent | ❌ | ❌ |
| Multi-turn reasoning | `orchestrator` | ❌ | ❌ |
| Tool use | `orchestrator`, `native_react` | ❌ | ❌ |
| Code generation | `native_openhands` | ❌ | ❌ |
| Research | `deep_research` | ❌ | ❌ |
| Monitoring | `monitor_operative` | ❌ | ❌ |
| Voice interaction | `speech` + TTS | ❌ | ❌ (SSML only) |
| Scheduled tasks | `scheduler` + Temporal | ❌ | ❌ |

### 4.3 Channel Comparison

| Channel | OpenJarvis | CityOS voice-assistant |
|---------|-----------|------------------------|
| Slack | ✅ | ❌ |
| Discord | ✅ | ❌ |
| Telegram | ✅ | ❌ |
| WhatsApp | ✅ | ❌ |
| Email | ✅ | ❌ |
| SMS (Twilio) | ✅ | ❌ |
| Webhook | ✅ | ✅ (basic) |
| WebChat | ✅ | ❌ |

---

## 5. Gap Analysis Matrix

### 5.1 Feature Gap (CityOS ai-assistant vs. OpenJarvis)

```
CityOS ai-assistant                OpenJarvis
┌─────────────────────┐           ┌─────────────────────────────┐
│ page.tsx (10 lines) │           │ 35+ CLI commands            │
│ "coming soon"       │           │ 14+ agents                  │
│                     │    vs.    │ 25+ channels                │
│ env.ts (22 lines)   │           │ 30+ tools                   │
│ (unused vars)       │           │ Desktop app                 │
│                     │           │ Rust extensions             │
│ Empty tests         │           │ Memory, traces, telemetry   │
│                     │           │ Skills (13,700+)            │
│                     │           │ Model fine-tuning           │
└─────────────────────┘           └─────────────────────────────┘
        ~5% maturity                       100% maturity
```

### 5.2 Feature Gap (CityOS voice-assistant vs. OpenJarvis)

```
CityOS voice-assistant             OpenJarvis
┌─────────────────────┐           ┌─────────────────────────────┐
│ Express server      │           │ Express + FastAPI servers   │
│ 3 hardcoded intents │           │ 25+ channel backends        │
│ SSML builder        │    vs.    │ faster-whisper (STT)        │
│ No AI model         │           │ TTS generation              │
│ No database calls   │           │ LLM orchestration           │
│ No memory           │           │ Session management          │
│ Empty tests         │           │ Evaluation suite            │
└─────────────────────┘           └─────────────────────────────┘
        ~15% maturity                      100% maturity
```

---

## 6. Strategic Recommendation

### 6.1 Core Principle

> **Do not build AI infrastructure in CityOS. Consume OpenJarvis as a service.**

CityOS should focus on what it does best:
- Multi-tenant surface runtime (SDUI, 14 surfaces)
- Domain-specific business logic (120+ domains)
- BFF gateway pattern with RBAC
- Keycloak identity and Walt.id credentials
- PostgreSQL + PostGIS data layer

OpenJarvis should handle:
- Model routing and inference
- Agent orchestration
- Tool dispatch (MCP)
- Memory and retrieval
- Channel integrations
- Trace recording and telemetry

### 6.2 Option A: Repurpose as Thin Frontends (Recommended)

**`apps/ai-assistant/` → OpenJarvis Chat Frontend**

```
Before: Placeholder page
After:  Next.js chat UI → BFF → OpenJarvis API
```

Implementation:
- Replace `page.tsx` with a full chat interface (similar to OpenJarvis desktop ChatPage)
- Use `@cityos/api-client-react` for BFF communication
- Consume OpenJarvis via BFF gateway (not directly)
- Render AI responses as SDUI blocks where applicable
- Add Keycloak auth via existing BFF `withBff()` wrapper

**`apps/voice-assistant/` → OpenJarvis Voice Gateway**

```
Before: Hardcoded intent handlers
After:  Express webhook → OpenJarvis agent → TTS → Voice response
```

Implementation:
- Keep Express server and webhook framework
- Replace hardcoded intents with OpenJarvis agent calls
- Add faster-whisper for STT (or use OpenJarvis `speech` tool)
- Add TTS output (Cartesia, or OpenJarvis TTS)
- Route citizen requests through appropriate OpenJarvis agent
- Maintain SSML builder for voice formatting

### 6.3 Option B: Archive and Replace (Not Recommended)

Delete `ai-assistant` and `voice-assistant` entirely; use OpenJarvis desktop app and API directly.

**Why not recommended**:
- CityOS needs tenant-scoped, RBAC-enforced AI access
- OpenJarvis desktop is single-user; CityOS needs multi-tenant
- CityOS surfaces require SDUI block rendering
- Branding and UX consistency across CityOS portals

### 6.4 Option C: Merge into Existing Surfaces (Alternative)

Instead of standalone apps, embed AI into existing surfaces:
- `smart-city-portal/` → Add chat widget using OpenJarvis
- `mobile/` → Add voice command using OpenJarvis
- `business-dashboard/` → Add merchant assistant using OpenJarvis
- `city-dashboard/` → Add ops monitoring using OpenJarvis

**This is the long-term vision**, but standalone `ai-assistant` and `voice-assistant` apps are still useful as:
- Reference implementations
- Admin/developer tools
- Fallback surfaces when domain-specific AI fails

---

## 7. Implementation Roadmap

### Phase 1: Connect (Week 1–2)
1. Deploy OpenJarvis container in `cityos-apps-backend` compose project
2. Add `OPENJARVIS_API_URL` and `OPENJARVIS_API_KEY` to CityOS `envValidator.ts`
3. Create BFF proxy route: `/api/bff/ai/chat` → forwards to OpenJarvis `/v1/chat/completions`
4. Verify health: `curl http://localhost:8000/health`

### Phase 2: ai-assistant Chat UI (Week 3–4)
1. Replace placeholder `page.tsx` with chat interface
2. Implement message history with Zustand or React Query
3. Add streaming SSE support
4. Integrate Keycloak auth
5. Add SDUI block rendering for structured responses
6. Write Playwright E2E tests

### Phase 3: voice-assistant Agent Bridge (Week 5–6)
1. Add OpenJarvis SDK/client to Express server
2. Replace hardcoded intents with dynamic agent routing
3. Integrate faster-whisper for STT
4. Add TTS output pipeline
5. Implement session/memory per caller
6. Write Vitest unit tests for intent routing

### Phase 4: Domain Tools (Week 7–10)
1. Build CityOS MCP server in `packages/domains/*/`
2. Expose domain tools: governance lookup, commerce status, etc.
3. Register tools with OpenJarvis
4. Test agent + tool combinations
5. Add human approval for privileged actions

### Phase 5: Polish (Week 11–12)
1. Add caching (Redis) for common queries
2. Implement rate limiting per tenant
3. Add analytics dashboard (Grafana)
4. Performance optimization
5. Security audit
6. Documentation update

---

## 8. Decision Log

| Decision | Rationale |
|----------|-----------|
| **Consume OpenJarvis, don't rebuild** | 12–18 months of AI engineering vs. 2–4 weeks of integration |
| **Keep ai-assistant as standalone app** | Reference implementation, admin tool, fallback surface |
| **Keep voice-assistant as standalone app** | Voice-specific UX patterns, webhook framework reusable |
| **Route through BFF, not direct** | Enforces RBAC, tenant isolation, audit logging |
| **Use local models by default** | Aligns with Intelligence Per Watt, reduces cloud costs |
| **Enable cloud fallback for complex queries** | Ensures service quality when local models insufficient |

---

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| OpenJarvis API changes | Medium | Medium | Pin version, use BFF proxy layer |
| Local model quality insufficient | Medium | High | Cloud fallback, continuous evaluation |
| Tenant isolation in OpenJarvis | Low | Critical | Enforce at BFF gateway, never trust client |
| Voice latency unacceptable | Medium | Medium | Streaming, caching, edge deployment |
| Skills ecosystem immaturity | Low | Low | Use built-in agents first, add skills later |
| Team skill gap (Python/Rust) | Medium | Medium | Train team, hire specialist, or managed service |

---

## See also

- [OpenJarvis Full Inventory](openjarvis-inventory.md) — Complete component catalog
- [Integration Overview](../integration/overview.md) — How CityOS connects to OpenJarvis
- [OpenJarvis Runtime Integration](../integration/openjarvis-runtime.md) — API connection details
- [MCP and Tool Integration](../integration/mcp-tools.md) — Domain tool exposure
- [Mobile and Expo Integration](../integration/mobile-expo-integration.md) — Voice on mobile
- [System Context](../architecture/system-context.md) — Trust boundaries and security
- [Testing Strategy](../operations/testing-strategy.md) — How to test the integration
