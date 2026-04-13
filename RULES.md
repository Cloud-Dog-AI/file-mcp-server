# file-mcp-server — Agent & Engineer Rules

**Version:** 3.0
**Date:** 2026-04-13
**Extends:** `cloud-dog-ai-platform-standards/RULES.md` v2.3 (2026-03-31)

> **PRIME DIRECTIVE — BINDING ON ALL AGENTS WORKING IN THIS REPOSITORY:**
> I WILL NEVER: LIE, FUDGE, HACK, FALSIFY, STUB, FAKE, HIDE, PRETEND, SKIP, BYPASS, FABRICATE, SUBSTITUTE, INVENT.
> IF I CANNOT GUARANTEE 100% COMPLIANCE, I WILL STOP AND SAY SO.
> IF TESTS FAIL, I WILL REPORT FAILURES HONESTLY.
> IF I DON'T KNOW, I WILL ASK, NOT GUESS.
>
> **§1.2 — The programme coordinator MUST independently verify ALL agent claims.**
> Every claim requires: independent grep/command execution, cross-reference evidence against source,
> spot-check fixes, reject on ANY discrepancy.

## Mandatory Reading Before ANY Work
1. Platform RULES.md — `cloud-dog-ai-platform-standards/RULES.md` (binding contract)
2. AGENT-LESSONS.md — `cloud-dog-ai-platform-standards/AGENT-LESSONS.md` (cross-platform knowledge, PC1-PC25)
3. This file — project-specific rules below
4. AGENT-BOOTSTRAP-DIRECTIVE.md — `cloud-dog-ai-platform-standards/working/AGENT-BOOTSTRAP-DIRECTIVE.md` (platform orientation)

## Relevant Platform Incidents
- §1.1 Falsification incident — relevant to all file-mcp work and all evidence files
- §1.3 Fabrication incident — relevant to all storage profiles, backend names, paths, URLs, ports, and report claims
- §1.5 Production firewall incident — relevant to all Docker/Terraform deployment work for this service

---

## Section 1 — Platform Rules (Inherited)

All rules from `cloud-dog-ai-platform-standards/RULES.md` v2.3 apply without exception:
- **§ 1** Integrity and honesty (non-negotiable)
- **§ 1.2** Coordinator verification mandate
- **§ 1.3** Fabrication incident record
- **§ 1.5** Production firewall incident protections
- **§ 2** Configuration precedence: `os.environ → env file → config.yaml → defaults.yaml`
- **§ 2.3** Credential management: Vault primary; `private/` only for credentials not yet in Vault
- **§ 2.4** Zero hardcoded values (zero tolerance)
- **§ 3** Server and process management (server_control.sh, Docker rules)
- **§ 4** Code and change management
- **§ 5** Testing rules (UT/ST/IT/AT hierarchy, real systems, forensic validation)
- **§ 6** Documentation standards (REQUIREMENTS, ARCHITECTURE, TESTS, TASKS, etc.)
- **§ 8.8** Coordinator forensic verification of agent claims
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

## Section 4A — Verified Port Assignments

Verified against [defaults.yaml](/opt/iac/Development/cloud-dog-ai/file-mcp-server/defaults.yaml):
- API server: `8060`
- Web server: `8061`
- MCP server: `8062`
- A2A server: `8063`

## Section 4B — Platform Incident Relevance

- **§1.1 Falsification** is directly relevant to file CRUD, RBAC denial proofs, and report claims.
- **§1.3 Fabrication** is directly relevant to storage profile names, scope roots, backend identifiers, URLs, and port assignments.
- **§1.5 Firewall** is directly relevant to any Docker/Terraform deployment or remote validation involving this service.

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
