<div align="center">
  <img alt="OpenJarvis" src="assets/OpenJarvis_Horizontal_Logo.png" width="400">

  <p><i>Personal AI, On Personal Devices.</i></p>

  <p>
    <a href="https://scalingintelligence.stanford.edu/blogs/openjarvis/"><img src="https://img.shields.io/badge/project-OpenJarvis-blue" alt="Project"></a>
    <a href="https://open-jarvis.github.io/OpenJarvis/"><img src="https://img.shields.io/badge/docs-mkdocs-blue" alt="Docs"></a>
    <img src="https://img.shields.io/badge/python-%3E%3D3.10-blue" alt="Python">
    <img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="License">
    <a href="https://discord.gg/6ZtCB94h5p"><img src="https://img.shields.io/badge/discord-join-7289da?logo=discord&logoColor=white" alt="Discord"></a>
    <a href="https://x.com/OpenJarvisAI"><img src="https://img.shields.io/badge/X-@OpenJarvisAI-black?logo=x&logoColor=white" alt="X / Twitter"></a>
  </p>
</div>

---

> **[Documentation](https://open-jarvis.github.io/OpenJarvis/)**
>
> **[Project Site](https://scalingintelligence.stanford.edu/blogs/openjarvis/)**
>
> **[Leaderboard](https://open-jarvis.github.io/OpenJarvis/leaderboard/)**
>
> **[Roadmap](https://open-jarvis.github.io/OpenJarvis/development/roadmap/)**

## Why OpenJarvis?

Personal AI agents are exploding in popularity, but nearly all of them still route intelligence through cloud APIs. Your "personal" AI continues to depend on someone else's server. At the same time, our [Intelligence Per Watt](https://www.intelligence-per-watt.ai/) research showed that local language models already handle 88.7% of single-turn chat and reasoning queries, with intelligence efficiency improving 5.3× from 2023 to 2025. The models and hardware are increasingly ready. What has been missing is the software stack to make local-first personal AI practical.

OpenJarvis is that stack. It is a framework for local-first personal AI, built around three core ideas: shared primitives for building on-device agents; evaluations that treat energy, FLOPs, latency, and dollar cost as first-class constraints alongside accuracy; and a learning loop that improves models using local trace data. The goal is simple: make it possible to build personal AI agents that run locally by default, calling the cloud only when truly necessary. OpenJarvis aims to be both a research platform and a production foundation for local AI, in the spirit of PyTorch.

---

## 🏙️ CityOSJarvis Fork

> This is the **Dakkah CityOS** fork of OpenJarvis, hardened for multi-tenant smart city deployments with Saudi compliance requirements.

### What Makes CityOSJarvis Different

| Feature | Upstream OpenJarvis | CityOSJarvis |
|---------|---------------------|--------------|
| Multi-tenancy | Single user | Node hierarchy (Global → Country → Region → City → Zone → POI → Tenant) |
| Auth | Local API key | Keycloak JWT (RS256) with realm roles |
| Compliance | None | PHI/PII blocking, Saudi ID/Iqama detection, Arabic health keywords |
| Audit | Console logs | Append-only JSON Lines with tenant isolation |
| Voice | STT only | STT + optional Cartesia TTS (`ENABLE_TTS=true`) |
| MCP Tools | Generic | 6 CityOS domain tools (governance, commerce, healthcare, transportation, fleet, public safety) |
| Monitoring | None | Prometheus metrics + Grafana dashboards |

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CityOS Web Platform                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Smart City  │  │  Business   │  │    City Dashboard       │  │
│  │   Portal    │  │  Dashboard  │  │   (Government)          │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                      │                │
│         └────────────────┼──────────────────────┘                │
│                          ▼                                       │
│              ┌─────────────────────┐                             │
│              │   BFF Gateway       │                             │
│              │   (/api/bff/ai/*)   │                             │
│              │   JWT + Tenant      │                             │
│              └──────────┬──────────┘                             │
└─────────────────────────┼────────────────────────────────────────┘
                          ▼
              ┌─────────────────────┐
              │   CityOSJarvis      │
              │   (Python :8000)    │
              │                     │
              │  ┌───────────────┐  │
              │  │ ComplianceGate│  │  ← Blocks PHI/PII before agent
              │  └───────────────┘  │
              │  ┌───────────────┐  │
              │  │CityOSAuditLog │  │  ← JSON Lines audit trail
              │  └───────────────┘  │
              │  ┌───────────────┐  │
              │  │ Voice Service │  │  ← STT (whisper) + TTS (cartesia)
              │  └───────────────┘  │
              │  ┌───────────────┐  │
              │  │  MCP Tools    │  │  ← 6 CityOS domain tools
              │  └───────────────┘  │
              └─────────────────────┘
```

### Quick Start for CityOS Developers

```bash
# 1. Clone the fork
git clone https://github.com/dakkah-core/CityOSJarvis.git
cd CityOSJarvis
git checkout cityos/main

# 2. Install with uv (Python 3.10+)
uv sync --extra server --extra scheduler --extra speech --extra browser --extra tools-search --extra channels --extra pdf --extra security-signing

# 3. Set required environment variables
export CITYOS_KEYCLOAK_URL="http://localhost:8080/realms/cityos"
export CARTESIA_API_KEY="your-cartesia-key"  # optional, for TTS
export ENABLE_TTS="true"  # optional

# 4. Start the server
uv run python -m openjarvis.server.app --host 0.0.0.0 --port 8000

# 5. Health check
curl http://localhost:8000/health
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CITYOS_KEYCLOAK_URL` | Yes | — | Keycloak issuer URL for JWT validation |
| `CITYOS_JWT_AUDIENCE` | No | `cityos-web` | JWT audience claim |
| `ENABLE_TTS` | No | `false` | Enable Cartesia text-to-speech |
| `CARTESIA_API_KEY` | No | — | Cartesia API key (required if TTS enabled) |
| `WHISPER_MODEL` | No | `base` | faster-whisper model size |
| `CUDA_VISIBLE_DEVICES` | No | — | GPU device for whisper |

### Docker

```bash
docker build -f deploy/docker/Dockerfile.cityos -t cityosjarvis:latest .
docker run -p 8000:8000 -e CITYOS_KEYCLOAK_URL=http://host.docker.internal:8080/realms/cityos cityosjarvis:latest
```

### Compliance Features

- **Saudi PII Detection**: National ID (10-digit), Iqama (10-digit), old format (`
- **Health PHI Detection**: Blood type, diagnosis keywords, medication names, surgery terms
- **Financial Data**: Credit cards (Visa, Mastercard, AMEX), Saudi IBANs
- **Secrets**: API keys, JWT tokens, high-entropy base64 strings
- **Arabic Support**: Native regex for Arabic health keywords and Saudi phone numbers (`+966`)

### Testing

```bash
# Python tests (147 tests)
uv run pytest tests/ -q

# Security tests (48 PHI injection cases)
uv run pytest tests/cityos/test_security_phi_injection.py -q

# Integration tests
uv run pytest tests/cityos/test_integration_chat.py -q
```

### Upstream Sync

This fork is automatically synced with upstream OpenJarvis monthly via `.github/workflows/upstream-sync.yml`.

---

## Installation (Original)

**macOS / Linux:**

```bash
curl -fsSL https://open-jarvis.github.io/OpenJarvis/install.sh | bash
```

The installer handles everything for you — including [uv](https://docs.astral.sh/uv/), the Python venv, Ollama, and a small starter model. You don't need to install anything first.

**Windows:** the installer is a `bash` script and won't run in PowerShell or `cmd`. Pick one of:

- **WSL2 (recommended for the CLI / Python SDK)** — one-time setup in an admin PowerShell, then run the same `curl ... | bash` inside Ubuntu:
  ```powershell
  wsl --install -d Ubuntu-24.04
  ```
  Open the Ubuntu shell that gets installed, then follow [WSL2 install instructions](https://open-jarvis.github.io/OpenJarvis/getting-started/wsl2/).
- **Desktop app** — download the [Windows installer (`.exe`)](https://github.com/open-jarvis/OpenJarvis/releases/download/desktop-v1.0.2/OpenJarvis_1.0.1_x64-setup.exe) from the latest [desktop release](https://github.com/open-jarvis/OpenJarvis/releases/tag/desktop-v1.0.2) (macOS `.dmg` and Linux `.deb`/`.rpm`/`.AppImage` are there too) for the GUI experience, no terminal required. **Prerequisite:** the desktop app expects [uv](https://docs.astral.sh/uv/) to be installed already — if it isn't, install it first in PowerShell, then launch the app:
  ```powershell
  powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

About 3 minutes on a typical broadband connection. Then:

```bash
jarvis
```

The Rust extension and bigger models continue downloading in the background while you chat. Run `jarvis doctor` to see status.

**Platforms:** macOS (Intel + Apple Silicon), Linux, WSL2 on Windows. Native Windows is not supported — use WSL2 or the desktop binary.

**Manual install / contributors:** see [docs/getting-started/install.md](docs/getting-started/install.md).

## Quick Start

```bash
curl -fsSL https://open-jarvis.github.io/OpenJarvis/install.sh | bash
jarvis
```

`jarvis init --preset <name>` switches to a starter config. Available presets: `morning-digest-mac`, `morning-digest-linux`, `morning-digest-minimal`, `deep-research`, `code-assistant`, `scheduled-monitor`, `chat-simple`.

## Starter Configs

Install any preset with one command:

```bash
uv run jarvis init --preset morning-digest-mac   # or any preset below
```

> Prefix every `jarvis ...` invocation with `uv run`, or activate the venv first (`source .venv/bin/activate`) so plain `jarvis ...` works for the rest of your shell session.

| Preset | Use Case | What it does |
|--------|----------|-------------|
| `morning-digest-mac` | Daily Briefing (Mac) | Spoken briefing from email, calendar, health, news with Jarvis voice |
| `morning-digest-linux` | Daily Briefing (Linux) | Same, with vLLM support for GPU servers |
| `morning-digest-minimal` | Daily Briefing (minimal) | Just Gmail + Calendar, runs on any machine |
| `deep-research` | Research Assistant | Multi-hop research across indexed docs with citations |
| `code-assistant` | Code Companion | Agent with code execution, file I/O, and shell access |
| `scheduled-monitor` | Persistent Monitor | Stateful agent that runs on a schedule with memory |
| `chat-simple` | Simple Chat | Lightweight conversation, no tools needed |

```bash
# Example: Morning Digest on Mac
uv run jarvis init --preset morning-digest-mac
uv run jarvis connect gdrive          # one OAuth flow covers Gmail, Calendar, Tasks
uv run jarvis digest --fresh          # generate and play your first briefing
```
