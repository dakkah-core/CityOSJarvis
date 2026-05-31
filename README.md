<div align="center">
  <img alt="OpenJarvis" src="assets/OpenJarvis_Horizontal_Logo.png" width="400">

  <p><i>Personal AI, On Personal Devices.</i></p>

  <p>
    <a href="https://scalingintelligence.stanford.edu/blogs/openjarvis/"><img src="https://img.shields.io/badge/project-OpenJarvis-blue" alt="Project"></a>
    <a href="https://open-jarvis.github.io/OpenJarvis/"><img src="https://img.shields.io/badge/docs-mkdocs-blue" alt="Docs"></a>
    <img src="https://img.shields.io/badge/python-%3E%3D3.10-blue" alt="Python">
    <img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="License">
  </p>
</div>

---

> **[Documentation](https://open-jarvis.github.io/OpenJarvis/)**
>
> **[Project Site](https://scalingintelligence.stanford.edu/blogs/openjarvis/)**

---

## 🏙️ CityOSJarvis — AI Engine

> This repository contains the **Python AI backend** for CityOSJarvis.
> All frontend surfaces, infrastructure configs, and documentation live in the
> **[dakkah-cityos-cms monorepo](https://github.com/dakkah-core/dakkah-cityos-cms)**.

### What's in this repo

| Path | Description |
|------|-------------|
| `src/openjarvis/` | Core AI engine (Python) — agents, LLM routing, orchestrator |
| `src/openjarvis/cityos/` | CityOS extensions — events, storage, search, Kuzzle, metrics, prompt guard, Arabic voice, MCP tools |
| `rust/` | Rust performance components |
| `tests/` | Python test suite |

### What's in the monorepo

| Path | Description |
|------|-------------|
| `apps/cityos-jarvis-desktop/` | Tauri desktop app |
| `apps/mobile/` | Expo citizen mobile app |
| `apps/mobile-driver/` | Fleet driver companion |
| `apps/mobile-inspector/` | Field inspector app |
| `packages/openjarvis-client/` | TypeScript SDK |
| `infra/k8s/cityosjarvis/` | Helm chart |
| `services/cityosjarvis/` | Docker Compose |

### Upstream

This is a fork of [OpenJarvis](https://github.com/open-jarvis/OpenJarvis).
Automated sync runs weekly via `.github/workflows/upstream-sync.yml`.

```bash
# Manual upstream sync
git fetch upstream main
git merge upstream/main
```
