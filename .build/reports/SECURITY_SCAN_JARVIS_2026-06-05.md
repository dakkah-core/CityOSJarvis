# CityOSJarvis Security Scan Report - 2026-06-05

## Scope

- Repository: `C:\Dakkah-CityOS\CityOSJarvis`
- Scope: tracked source/config paths only.
- Excluded: untracked `.env`, private keys, and secret material.
- VPS access: read-only observation and smoke checks only.

## Threat Model

- Public server binds must require non-default API key material.
- Managed-agent APIs must not let an authenticated caller self-authorize local shell/code/file-write tools.
- Existing managed-agent rows must not bypass route-level create/update controls during streaming or scheduled execution.
- Docker/compose profiles must not ship predictable bearer defaults.

## Findings And Disposition

| Severity | Finding | Disposition |
|---|---|---|
| High | Managed-agent APIs could accept caller-provided `config.tools` containing shell/code execution tools and auto-confirm them. | Fixed locally: dangerous managed-agent tools are rejected by default at create/update/template/stream execution, and scheduler execution sanitizes existing configs unless explicitly opted in via `agent_manager.allow_dangerous_tools=true`. |
| High | Non-loopback server binds only rejected empty API keys, not known default keys. | Fixed locally: known default keys such as `cityos-local-key` and `staging-key` are rejected on non-loopback binds. |
| High | Docker compose profiles included predictable API/LiteLLM key defaults. | Fixed locally: compose profiles now require supplied `OPENJARVIS_API_KEY` and `LITELLM_MASTER_KEY`; `.env.example` uses neutral replacement placeholders. |

## Validation

- `uv run ruff check src tests` passed.
- `uv run ruff format --check src tests` passed.
- `uv run pyright src/openjarvis/cityos` passed.
- `uv run pytest --basetemp C:\Dakkah-CityOS\.tmp-cityosjarvis-pytest\full-after-security --tb=short -q` passed: 7232 passed, 151 skipped, 12 warnings.
- Local Docker proof rebuilt `cityosjarvis:codex-test`, ran `cityosjarvis-codex-test` on `127.0.0.1:18010`, `/health` returned `{"status":"ok"}`, and the test container was removed.

## Acceptance

No unresolved high or critical Jarvis findings remain in the reviewed scope. Enabling dangerous managed-agent tools is now an explicit opt-in that should be limited to trusted local or isolated deployments.
