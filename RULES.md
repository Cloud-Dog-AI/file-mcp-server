# file-mcp-server — Agent & Engineer Rules

**Version:** 2.0
**Date:** 2026-03-04
**Parent:** `cloud-dog-ai-platform-standards/RULES.md` v1.5

> **⛔ BINDING CONTRACT:** This document extends the platform-wide rules.
> Read the parent [Cloud-Dog AI Platform Common Rules](../cloud-dog-ai-platform-standards/RULES.md) **IN FULL** first.
> ALL platform rules apply without exception. This file adds project-specific rules ONLY.

---

## Section 1 — Platform Rules (Inherited)

All rules from `cloud-dog-ai-platform-standards/RULES.md` v1.5 apply without exception:
- **§ 1** Integrity and honesty (non-negotiable)
- **§ 2** Configuration precedence: `os.environ → env file → config.yaml → defaults.yaml`
- **§ 2.3** Credential management: Vault primary; `private/` only for credentials not yet in Vault
- **§ 2.4** Zero hardcoded values (zero tolerance)
- **§ 3** Server and process management (server_control.sh, Docker rules)
- **§ 4** Code and change management (approval rules, code standards, UK English)
- **§ 5** Testing rules (UT/ST/IT/AT hierarchy, real systems, forensic validation)
- **§ 6** Documentation standards (REQUIREMENTS, ARCHITECTURE, TESTS, TASKS, etc.)
- **§ 7** Repository structure
- **§ 8** Operational controls (timeouts, stop controls, verification)
- **§ 9** Security boundaries (project confinement, credential boundaries, network boundaries, scope discipline)
- **§ 10** Infrastructure protection (Vault config read-only, Terraform read-only)
- **§ 11** Vault path verification (never invent paths, query first)
- **§ 12** Implementation truthfulness (never claim done without evidence)
- **Mandatory Completion Warranty** required on every task completion

---

## Section 2 — Vault Configuration

### Load before any operation
```bash
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
```

### Validate access
```bash
bash scripts/validate-vault.sh
```

### Vault sections used by this project
- `dev.storage` — S3/WebDAV/FTP backend credentials
- `dev.keys` — API keys
- `dev.repository` — PyPI/NPM registry credentials

---

## Section 3 — Credential Management

### Standard test env files (committed, non-secret)
- `tests/env-UT` — unit test config
- `tests/env-ST` — system test config
- `tests/env-IT` — integration test config

### Rules
- All credentials MUST be stored in Vault or `private/` (git-ignored) — never committed
- NEVER commit real API keys, storage credentials, or tokens
- NEVER log raw credentials (enforced by `cloud_dog_logging` redaction)

---

## Section 4 — Platform Package Rules

### MUST use (no bespoke alternatives)
| Concern | Package | Bespoke alternative forbidden |
|---------|---------|------------------------------|
| Config loading | `cloud_dog_config` | No custom env/YAML loaders |
| Logging | `cloud_dog_logging` | No custom structlog setup |
| API factory | `cloud_dog_api_kit` | No raw FastAPI() instantiation |
| Auth/RBAC | `cloud_dog_idam` | No custom JWT/API key/RBAC code |

### Installation
```bash
pip install -e ".[dev]" --index-url https://pypi.cloud-dog.net/simple/
```

---

## Section 5 — Project-Specific Rules

### 5.1 Service Scope
- File tooling only — no LLM integration, no internet crawling, no web search
- Operate only inside configured scope roots
- Never edit audit logs or snapshots directly

### 5.2 Project Boundaries
- Do not re-run completed migration phases (CONFIG, LOGGING, API-KIT, IDAM) unless explicitly instructed
- Do not modify repositories outside `file-mcp-server` from this project workflow

---

*Last updated: 2026-03-04*
