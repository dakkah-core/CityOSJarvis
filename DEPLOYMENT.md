# CityOSJarvis Deployment Guide

> Complete deployment pipeline for CityOSJarvis — local Docker, VPS integration, and client app builds.

---

## Table of Contents

1. [Local Development](#local-development)
2. [Docker (Standalone)](#docker-standalone)
3. [Docker (Integrated with CityOS)](#docker-integrated-with-cityos)
4. [VPS Deployment](#vps-deployment)
5. [Client App Builds](#client-app-builds)
   - [Web Platform](#web-platform)
   - [Desktop (Tauri)](#desktop-tauri)
   - [Mobile (Expo)](#mobile-expo)
6. [GitHub Actions CI/CD](#github-actions-cicd)
7. [Troubleshooting](#troubleshooting)

---

## Local Development

### Prerequisites

- Python 3.10+ (or `uv` for faster setup)
- Rust toolchain (for Tauri desktop builds)
- Node.js 22+ (for web/mobile builds)
- Docker & Docker Compose (for containerized stack)

### Backend

```bash
# Install dependencies
uv sync --all-extras

# Run with local settings
export OPENJARVIS_API_KEY=cityos-local-key
export DATABASE_URL=postgresql://jarvis:jarvis@localhost:5432/jarvis
export REDIS_URL=redis://localhost:6379/0
uv run python -m openjarvis.main
```

### Tests

```bash
# Python tests (448 tests)
uv run pytest tests/ -q

# TypeScript tests (130 tests)
cd packages/openjarvis-client && pnpm test
```

---

## Docker (Standalone)

Run the complete CityOSJarvis stack locally without the CityOS monorepo:

```bash
cd deploy/docker
docker compose -f docker-compose.cityos.yml up -d
```

Services:

| Service | Port | Description |
|---------|------|-------------|
| CityOSJarvis | 8000 | FastAPI backend |
| Ollama | 11434 | Local LLM inference |
| Postgres | 5433 | Jarvis database |
| Redis | 6380 | Cache / sessions |
| Loki | 3100 | Log aggregation |
| Promtail | — | Log shipping |

### Environment Variables

Create a `.env` file in `deploy/docker/`:

```env
OPENJARVIS_API_KEY=cityos-local-key
KEYCLOAK_URL=http://host.docker.internal:8080
DATABASE_URL=postgresql://jarvis:jarvis@postgres:5432/jarvis
REDIS_URL=redis://redis:6379/0
CARTESIA_API_KEY=          # Optional: for TTS
ENABLE_TTS=false
LOKI_URL=http://loki:3100
```

---

## Docker (Integrated with CityOS)

Attach CityOSJarvis to the existing CityOS monorepo network:

```bash
# From the CityOS monorepo root
cd C:\Dakkah-CityOS\dakkah-cityos-cms

# Start CityOSJarvis alongside existing services
docker compose -f docker-compose.yml \
  -f ../CityOSJarvis/deploy/docker/docker-compose.integrated.yml \
  up -d cityosjarvis

# Or with the full VPS compose
docker compose -f docker-compose.vps.yml --profile ai up -d cityosjarvis
```

CityOSJarvis connects to:
- **Postgres** — existing `cityos-postgres` container (creates `jarvis` DB)
- **Redis** — existing `cityos-redis` container
- **Keycloak** — existing `cityos-keycloak` container
- **Loki** — existing `cityos-infra_loki` container
- **Traefik** — auto-registered route at `/jarvis`

---

## VPS Deployment

### 1. Set GitHub Secrets

In `Settings > Secrets and variables > Actions`:

| Secret | Description |
|--------|-------------|
| `VPS_HOST` | VPS IP or hostname |
| `VPS_USER` | SSH username |
| `VPS_SSH_KEY` | Private key for SSH |
| `VPS_PORT` | SSH port (default 22) |
| `GITHUB_TOKEN` | Auto-provided |

### 2. Deploy

The workflow triggers on:
- Push to `cityos/main`
- Semver tags (`v*`)
- Manual dispatch (choose staging or production)

```bash
# Manual trigger via GitHub UI
# Actions > Deploy to VPS > Run workflow
```

### 3. VPS Compose Integration

The monorepo's `docker-compose.vps.yml` already includes the `cityosjarvis` service. On the VPS:

```bash
cd /opt/dakkah-cityos-cms-src

# Pull latest image
docker pull ghcr.io/dakkah/cityosjarvis:latest

# Deploy with AI profile
docker compose -f docker-compose.vps.yml --profile ai up -d cityosjarvis

# Verify health
curl -fs http://localhost:8000/health
```

---

## Client App Builds

### Web Platform

```bash
cd apps/web-platform

# Development
pnpm dev

# Production build
pnpm build

# The web platform consumes CityOSJarvis via the BFF gateway at:
#   /bff/ai/jarvis/chat
#   /bff/ai/jarvis/voice
#   /bff/ai/jarvis/agents
```

### Desktop (Tauri)

```bash
cd apps/cityos-jarvis-desktop

# Install dependencies
pnpm install

# Development (hot-reload)
pnpm tauri dev

# Build for current platform
pnpm tauri build

# Cross-platform builds
./scripts/build-desktop.sh    # macOS/Linux
.\scripts\build-desktop.ps1   # Windows

# Outputs:
#   src-tauri/target/release/bundle/msi/*.msi
#   src-tauri/target/release/bundle/dmg/*.dmg
#   src-tauri/target/release/bundle/appimage/*.AppImage
#   src-tauri/target/release/bundle/deb/*.deb
```

**Code signing:**
- macOS: Set `APPLE_SIGNING_IDENTITY` env var
- Windows: Requires code signing certificate for auto-updater

### Mobile (Expo)

```bash
cd apps/mobile

# Development
pnpm dev:mobile

# EAS build (requires Expo account + credentials)
pnpm eas:build --platform ios
pnpm eas:build --platform android

# OTA update
pnpm eas:ota
```

**Required setup:**
1. `eas login` — authenticate with Expo
2. `eas build:configure` — one-time project setup
3. iOS: Apple Developer account + provisioning profiles
4. Android: Upload keystore to EAS

---

## GitHub Actions CI/CD

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `docker-build.yml` | PR / push | Build & push multi-arch image |
| `vps-deploy.yml` | push `cityos/main`, tags | Deploy to VPS via SSH |
| `python-tests.yml` | PR / push | 448 Python tests |
| `typescript-tests.yml` | PR / push | 130 TypeScript tests |
| `security-scan.yml` | PR / push | Gitleaks, Trivy, Bandit, pip-audit |
| `upstream-sync.yml` | Daily | Sync upstream OpenJarvis changes |

### Branch Protection

Enable in GitHub Settings:
- `Settings > Branches > cityos/main`
  - ☑ Require a pull request before merging
  - ☑ Require status checks to pass
  - ☑ Require signed commits *(manual — GitHub UI only)*

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Module not found` for workspace packages | Run `pnpm install` in monorepo root |
| Postgres connection refused | Ensure `postgres` container is healthy: `docker compose ps` |
| Whisper model slow | Use GPU: set `CUDA_VISIBLE_DEVICES=0` |
| TTS returns 503 | Set `ENABLE_TTS=true` and provide `CARTESIA_API_KEY` |
| Keycloak auth fails | Verify `KEYCLOAK_URL` is reachable from container |
| Desktop build fails on Windows | Install Visual Studio Build Tools + Windows SDK |
| Mobile EAS build fails | Run `eas build:configure` and check credentials |
| Loki logs not appearing | Check `ENABLE_LOKI=true` and Loki container health |

---

*Last updated: 2026-05-29*
