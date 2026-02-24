This project follows the [Cloud-Dog AI Platform Common Rules](/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-platform-standards/RULES.md).

# File MCP Server Rules

## Binding Contract
- The platform Common Rules are mandatory and take precedence for integrity, configuration precedence, security boundaries, and test execution rules.
- This file defines project-specific constraints only.

## Project Scope
- Service scope is file tooling only.
- No LLM integration in this service.
- No internet crawling or web search features in this service.

## Security Boundaries
- Follow platform RULES.md Section 9 (Agent Security Boundaries) in full.
- Operate only inside configured scope roots.
- Never commit credentials, tokens, or secrets.
- Never edit audit logs or snapshots directly.

## Runtime and Operations
- Use `server_control.sh` for lifecycle control.
- Every server operation and pytest run must pass `--env <path>`.
- Standard test env files are `tests/env-UT`, `tests/env-ST`, and `tests/env-IT`.
- Source Vault before IT/AT runs that require real external services:
  - `set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a`

## Test Tier Ownership
- `tests/unit/`: isolated logic verification.
- `tests/system/`: real local system behaviour checks.
- `tests/integration/`: running API/server and cross-component behaviour.
- `tests/application/`: full workflow scenarios.

## Project Boundaries
- Do not re-run completed migration phases (CONFIG, LOGGING, API-KIT, IDAM) unless explicitly instructed.
- Do not modify repositories outside `file-mcp-server` from this project workflow.

## Completion Requirement
- Completion reports must include the platform RULES.md compliance warranty from Common Rules § Mandatory Completion Warranty.
