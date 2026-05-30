---
title: OpenJarvis Integration Strategy — Monorepo vs. External vs. Fork
description: Architectural decision record for how CityOS should incorporate OpenJarvis — copy, split, fork, or consume as external service.
---

# OpenJarvis Integration Strategy

> [← Back to CityOS Integrations](../index.md) · [← Gap Analysis](cityos-ai-gap-analysis.md) · [← Inventory](openjarvis-inventory.md)

---

## 1. The Question

> "What if we copy OpenJarvis to our repo under `apps/`? Do we split it into more than one app for better control? Do we keep it linked to the original GitHub for updates?"

This document analyzes three integration strategies:

| Strategy | Description |
|----------|-------------|
| **A. Monorepo Copy** | Copy all OpenJarvis code into `apps/openjarvis-*` |
| **B. External Dependency** | Consume OpenJarvis via Docker / git submodule / npm/pip package |
| **C. Fork + Hybrid** | Fork to CityOS org, consume as external, build thin wrappers in monorepo |

---

## 2. Understanding the Codebase Size

Before deciding, understand what we'd be importing:

| Component | Language | Files | Build Tool |
|-----------|----------|-------|------------|
| Python backend | Python 3.10+ | ~400 files | uv + hatchling |
| Rust extensions | Rust | ~200 files | Cargo |
| Desktop app | Tauri + TS | ~150 files | Cargo + Vite |
| Frontend SPA | React + TS | ~100 files | Vite |
| Docs | Markdown | ~200 files | MkDocs |
| Tests | Python + Rust | ~300 files | pytest + cargo test |
| CI/CD | YAML | ~15 files | GitHub Actions |

**Total**: ~1,400 files across 3 build systems (uv/hatchling, Cargo, Vite)

CityOS uses:
- pnpm workspace (TypeScript/Next.js)
- Some Python (ERPNext, Tryton)
- No Rust in apps/

---

## 3. Strategy A: Monorepo Copy

### 3.1 Approach
Copy OpenJarvis into CityOS under:
```
apps/
  openjarvis-api/          # Python backend
  openjarvis-desktop/      # Tauri desktop
  openjarvis-frontend/     # React SPA
  openjarvis-rust/         # Rust crates
```

### 3.2 Pros

| Advantage | Explanation |
|-----------|-------------|
| Single repo | One `git clone`, one PR process, one CI pipeline |
| Unified tooling | Can share linting, formatting, pre-commit hooks |
| Atomic changes | Change OpenJarvis + CityOS consumer in same PR |
| No network deps | Build doesn't depend on external repos being up |
| Full control | Can modify any line of OpenJarvis code |

### 3.3 Cons

| Disadvantage | Explanation |
|--------------|-------------|
| **Build system mismatch** | CityOS uses pnpm; OpenJarvis uses uv + Cargo. pnpm can't build Python/Rust |
| **CI complexity** | GitHub Actions need Python, Rust, AND Node.js matrices |
| **Version drift** | Can't easily pull upstream fixes without manual copy-paste |
| **Repository bloat** | +1,400 files, +300MB, mix of languages in monorepo |
| **Contributor confusion** | Python/Rust devs need to understand pnpm workspace rules |
| **Merge conflicts** | Every upstream update is a manual merge |
| **Security audits** | SCA tools (Snyk, Dependabot) need multi-language support |

### 3.4 Should We Split Into Multiple Apps?

If copying, we could split OpenJarvis into:

```
apps/
  openjarvis-api/          # Python: CLI + server + agents + tools
  openjarvis-channels/     # Python: 25+ channel backends
  openjarvis-desktop/      # Tauri: Desktop app
  openjarvis-frontend/     # React: Shared frontend
packages/
  openjarvis-rust/         # Rust: 17 crates
  openjarvis-python-sdk/   # Python: SDK for consumers
```

**Splitting benefits**:
- Independent versioning per component
- Team ownership (API team, desktop team, channels team)
- Selective deployment (deploy API without desktop)

**Splitting costs**:
- Tight coupling: desktop depends on frontend; Python depends on Rust (PyO3)
- Cross-app builds become complex
- Dependency management between split apps
- OpenJarvis wasn't designed as separate packages

**Verdict on splitting**: Not recommended if copying monorepo. OpenJarvis is architected as a unified system. Splitting it would require significant refactoring.

---

## 4. Strategy B: External Dependency

### 4.1 Approach
Keep OpenJarvis as external. CityOS consumes it via:

```yaml
# docker-compose.full.yml
services:
  openjarvis:
    image: ghcr.io/open-jarvis/openjarvis:latest
    ports:
      - "8000:8000"
    volumes:
      - openjarvis-data:/app/data
```

CityOS apps call it via HTTP:
```typescript
// apps/ai-assistant/src/lib/openjarvis.ts
const response = await fetch(`${OPENJARVIS_URL}/v1/chat/completions`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${OPENJARVIS_API_KEY}` },
  body: JSON.stringify({ model: 'ollama', messages: [...] })
});
```

### 4.2 Pros

| Advantage | Explanation |
|-----------|-------------|
| Clean separation | CityOS stays TypeScript/Next.js; OpenJarvis stays Python/Rust |
| Easy updates | `docker pull` gets latest upstream |
| No build system conflict | pnpm workspace unchanged |
| Repository size | CityOS stays lean |
| Independent scaling | OpenJarvis can run on GPU nodes, CityOS on CPU nodes |
| Upstream contributions | Can contribute fixes back to OpenJarvis project |

### 4.3 Cons

| Disadvantage | Explanation |
|--------------|-------------|
| Cross-repo changes | OpenJarvis change + CityOS change need 2 PRs |
| Network dependency | Build requires OpenJarvis image/registry |
| CityOS customizations | Can't easily patch OpenJarvis for CityOS-specific needs |
| Version pinning | Need to track which OpenJarvis version CityOS supports |
| Configuration drift | `.env` vars need to stay in sync across repos |
| Debugging | Harder to step-debug across repo boundaries |

### 4.4 Variants

| Variant | Mechanism | Best For |
|---------|-----------|----------|
| Docker image | `docker pull ghcr.io/open-jarvis/openjarvis` | Production deployment |
| Git submodule | `git submodule add` | Development with source access |
| Git subtree | `git subtree pull` | Merging upstream while keeping local changes |
| pip package | `uv pip install openjarvis` | If OpenJarvis publishes to PyPI |
| npm package | `npm install @openjarvis/sdk` | For TypeScript SDK (doesn't exist yet) |

---

## 5. Strategy C: Fork + Hybrid (Recommended)

### 5.1 Approach

```
┌─────────────────────────────────────────────────────────────┐
│  CityOS Monorepo (github.com/dakkah/cityos)                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  apps/ai-assistant/        # Thin Next.js chat UI   │    │
│  │  apps/voice-assistant/     # Thin Express gateway   │    │
│  │  packages/openjarvis-client/  # TypeScript SDK      │    │
│  │  packages/domains/*/       # CityOS MCP tools       │    │
│  │  (pnpm workspace — unchanged)                       │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                   │
│                          │ HTTP / MCP                        │
│                          ▼                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  OpenJarvis Fork (github.com/dakkah/openjarvis)     │    │
│  │  (origin: github.com/open-jarvis/OpenJarvis)        │    │
│  │  ├─ Python backend + agents + tools                 │    │
│  │  ├─ Rust extensions                                 │    │
│  │  ├─ Desktop app                                     │    │
│  │  └─ CityOS-specific patches (MCP adapters, configs) │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 How the Fork Works

**Step 1**: Fork `open-jarvis/OpenJarvis` → `dakkah/openjarvis`

**Step 2**: Add upstream remote:
```bash
git clone https://github.com/dakkah/openjarvis.git
cd openjarvis
git remote add upstream https://github.com/open-jarvis/OpenJarvis.git
git fetch upstream
```

**Step 3**: CityOS-specific changes in the fork:
- Custom MCP server configs for CityOS domains
- Pre-built Docker image with CityOS extras:
  ```dockerfile
  FROM openjarvis:latest
  RUN uv sync --extra inference-vllm --extra memory-faiss --extra scheduler --extra server
  COPY cityos-mcp-config.toml /app/config/
  ```
- CityOS branding in desktop app
- Arabic language support patches

**Step 4**: Consume in CityOS via Docker Compose:
```yaml
# CityOS docker-compose.full.yml
services:
  openjarvis:
    image: ghcr.io/dakkah/openjarvis:cityos-v1.2.0
    # or build from fork:
    # build: ../openjarvis/deploy/docker
```

**Step 5**: Pull upstream updates monthly:
```bash
git fetch upstream
git merge upstream/main
# Resolve conflicts, test, tag as cityos-v1.3.0
```

### 5.3 What Stays in CityOS Monorepo

Thin wrappers only — no AI logic:

```
apps/
  ai-assistant/              # Next.js chat UI
    src/
      app/
        page.tsx             # Chat interface
        api/chat/route.ts    # Server-side proxy to OpenJarvis
      components/
        ChatInput.tsx
        MessageList.tsx
        StreamingMessage.tsx
      lib/
        openjarvis-client.ts # Wrapper around fetch()
        
  voice-assistant/           # Express voice gateway
    src/
      index.ts               # Express server
      intents/
        router.ts            # Route to OpenJarvis agent
      lib/
        openjarvis-client.ts # Same client SDK
        stt.ts               # faster-whisper wrapper
        tts.ts               # TTS engine wrapper
        
packages/
  openjarvis-client/         # Shared TypeScript SDK
    src/
      client.ts              # Typed OpenJarvis API client
      types.ts               # OpenAPI schema types
      hooks.ts               # React Query hooks
```

### 5.4 Pros of Fork + Hybrid

| Advantage | Explanation |
|-----------|-------------|
| Best of both worlds | CityOS stays clean; OpenJarvis is customizable |
| Upstream tracking | Monthly merges keep security patches flowing |
| CityOS patches | Can add Arabic support, domain MCP configs, branding |
| Independent scaling | OpenJarvis runs on GPU nodes; CityOS on standard nodes |
| Clean monorepo | Only thin TS wrappers in pnpm workspace |
| Contribution path | Can upstream generic fixes to OpenJarvis project |
| Version pinning | CityOS docker-compose pins to `cityos-v1.2.0` tag |

### 5.5 Cons of Fork + Hybrid

| Disadvantage | Explanation |
|--------------|-------------|
| Two repos to manage | CityOS + openjarvis forks |
| Merge effort | Monthly upstream merges require engineering time |
| Divergence risk | CityOS patches may conflict with upstream changes |
| CI complexity | Need CI in both repos; integration tests across repos |
| Documentation | Need docs for "how to update OpenJarvis" |

---

## 6. Comparative Decision Matrix

| Criteria | A. Monorepo Copy | B. External | C. Fork + Hybrid |
|----------|------------------|-------------|------------------|
| **Repository size** | ❌ Bloated (+1,400 files) | ✅ Lean | ✅ Lean |
| **Build complexity** | ❌ 3 build systems | ✅ 1 build system | ✅ 1 build system |
| **CI complexity** | ❌ High | ✅ Low | ⚠️ Medium |
| **Upstream updates** | ❌ Manual copy-paste | ✅ `docker pull` | ⚠️ `git merge` |
| **CityOS customization** | ✅ Full control | ❌ Limited | ✅ Patchable |
| **Atomic PRs** | ✅ Single PR | ❌ 2 PRs | ⚠️ 2 PRs |
| **Team onboarding** | ❌ Must learn Python/Rust | ✅ Focus on TS | ✅ Focus on TS |
| **Scalability** | ⚠️ All on same nodes | ✅ Separate scaling | ✅ Separate scaling |
| **Debugging** | ✅ Single repo | ⚠️ Cross-repo | ⚠️ Cross-repo |
| **Security audits** | ❌ Multi-language SCA | ✅ Standard | ✅ Standard |
| **Long-term maintainability** | ❌ High burden | ⚠️ Dependency risk | ✅ Sustainable |
| **Time to implement** | ❌ Weeks (refactor) | ✅ Days | ✅ Days |

---

## 7. Recommendation

### Primary Recommendation: **Strategy C — Fork + Hybrid**

```
1. Fork open-jarvis/OpenJarvis → dakkah/openjarvis
2. Build CityOS-specific Docker image from fork
3. Add to CityOS docker-compose as external service
4. Build thin wrappers in CityOS monorepo only
5. Merge upstream monthly
```

### Why Not Strategy A (Monorepo Copy)?

- **Build system mismatch is fatal**. pnpm can't build Python/Rust. We'd need parallel CI pipelines in the same repo.
- **Repository bloat**. CityOS would grow by ~300MB and +1,400 files, making clones slower and IDE indexing heavier.
- **Update nightmare**. Every OpenJarvis release requires manual copy-paste or complex git subtree management.
- **Contributor confusion**. TypeScript developers would see Python/Rust code in PR reviews and get confused about conventions.

### Why Not Pure Strategy B (External)?

- **Can't patch for CityOS needs**. We need Arabic language support, custom MCP configs, and domain-specific prompts. External dependency prevents this.
- **No control over roadmap**. If OpenJarvis deprecates a feature CityOS relies on, we're stuck.

### Why Strategy C Wins

- **CityOS stays focused**. The monorepo remains a TypeScript/Next.js platform.
- **OpenJarvis is customizable**. The fork allows patches while tracking upstream.
- **Sustainable long-term**. Monthly merges are a known, manageable process.
- **Production proven**. This is how companies like Shopify, Vercel, and GitHub manage forks of open-source dependencies.

---

## 8. Implementation Plan

### Week 1: Fork and Setup

```bash
# 1. Fork on GitHub
#    open-jarvis/OpenJarvis → dakkah/openjarvis

# 2. Clone and configure
git clone https://github.com/dakkah/openjarvis.git
cd openjarvis
git remote add upstream https://github.com/open-jarvis/OpenJarvis.git

# 3. Create CityOS branch
git checkout -b cityos/main

# 4. Add CityOS Dockerfile
cp deploy/docker/Dockerfile deploy/docker/Dockerfile.cityos
# Edit: add uv sync --extra inference-vllm --extra memory-faiss --extra scheduler --extra server

# 5. Build and publish
docker build -f deploy/docker/Dockerfile.cityos -t ghcr.io/dakkah/openjarvis:cityos-v1.0.0 .
docker push ghcr.io/dakkah/openjarvis:cityos-v1.0.0
```

### Week 2: CityOS Integration

```bash
# In CityOS repo:
# 1. Add to docker-compose.full.yml
# 2. Add env vars to .env.example and envValidator.ts
# 3. Create packages/openjarvis-client/ TypeScript SDK
# 4. Wire apps/ai-assistant/ to use the SDK
# 5. Wire apps/voice-assistant/ to use the SDK
```

### Week 3: First CityOS Patch

```bash
# In dakkah/openjarvis fork:
# 1. Add CityOS MCP config
# 2. Add Arabic prompt templates
# 3. Add Keycloak JWT auth middleware patch
# 4. Tag as cityos-v1.1.0
# 5. Update CityOS docker-compose to new tag
```

### Ongoing: Monthly Upstream Sync

```bash
# Monthly maintenance (automated via GitHub Actions):
git fetch upstream
git merge upstream/main
# Run tests
# Tag: cityos-v1.2.0
# Build and push Docker image
# Create PR in CityOS to update docker-compose tag
```

---

## 9. File Structure (Recommended)

### CityOS Monorepo (unchanged structure)

```
dakkah-cityos-cms/
├── apps/
│   ├── ai-assistant/              # Thin Next.js chat UI
│   ├── voice-assistant/           # Thin Express voice gateway
│   ├── smart-city-portal/         # (add chat widget)
│   ├── ... (other CityOS apps)
├── packages/
│   ├── openjarvis-client/         # NEW: TypeScript SDK
│   ├── domains/
│   │   ├── governance/
│   │   ├── commerce/
│   │   └── ... (MCP tools here)
│   └── ...
├── docker-compose.full.yml        # references openjarvis image
└── .env.example                   # OPENJARVIS_API_URL, OPENJARVIS_API_KEY
```

### OpenJarvis Fork (separate repo)

```
dakkah-openjarvis/               # Fork of open-jarvis/OpenJarvis
├── src/openjarvis/              # Python backend (unchanged)
├── rust/                        # Rust extensions (unchanged)
├── frontend/                    # React SPA (unchanged)
├── desktop/                     # Tauri app (CityOS-branded patches)
├── deploy/docker/Dockerfile.cityos  # NEW: CityOS-specific build
├── configs/cityos/              # NEW: CityOS MCP configs
│   ├── mcp-servers.toml
│   └── prompts/
└── .github/workflows/
    └── upstream-sync.yml        # NEW: Monthly sync automation
```

---

## 10. Answering Your Specific Questions

### Q: "What if we copy OpenJarvis to our repo under `apps/`?"

**Don't.** It bloats the repo, breaks the build system, and makes updates impossible. The tech stacks are incompatible (pnpm vs. uv + Cargo).

### Q: "Do we split it under more than one app for better control?"

**No.** OpenJarvis is architected as a unified system. Splitting it would require refactoring 1,400 files and create tight coupling between the splits. Keep it as one service.

### Q: "Do we keep it linked to original GitHub for updates?"

**Yes, via a fork.** Fork `open-jarvis/OpenJarvis` → `dakkah/openjarvis`, add upstream remote, and merge monthly. This gives you:
- Security patches from upstream
- Ability to contribute fixes back
- Clean upgrade path
- CityOS-specific patches in the fork

---

## See also

- [CityOS AI Gap Analysis](cityos-ai-gap-analysis.md) — Current state of CityOS AI apps
- [OpenJarvis Full Inventory](openjarvis-inventory.md) — Complete component catalog
- [Integration Overview](../integration/overview.md) — How CityOS connects to OpenJarvis
- [Deployment Overview](../deployment/overview.md) — Docker Compose deployment patterns
- [System Context](../architecture/system-context.md) — Trust boundaries and network segmentation
