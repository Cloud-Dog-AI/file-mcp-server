# Agent lessons — file-mcp-server

Last reviewed: 2026-07-21
Scope: durable project-specific knowledge only.

## Authority and use

The binding programme rules and cross-programme lessons are in
`../cloud-dog-ai-platform-standards/RULES.md` and
`../cloud-dog-ai-platform-standards/AGENT-LESSONS.md`. This file is an overlay:
central authority wins on conflict. Read current project source, canonical docs, the
exact instruction and SSOT before acting.

Mutable versions, ports, endpoints, credentials, counts and lane states are not
authority here; resolve them from current configuration, manifests and source.

## Current project knowledge

- **FILE-PROFILE-001 — Profile propagation.** The selected file profile travels end to
  end through UI state, request headers, authentication, tool registry and runtime
  backend selection. Trace that path before changing browse/search behaviour.
- **FILE-RBAC-001 — Two permission layers.** Admin/profile HTTP protection and file-tool
  read/write permission are separate. Prove the MCP tool permission check itself before
  claiming reader/writer enforcement.
- **FILE-PROXY-001 — Proxy versus client.** The Web proxy owns forwarding and path
  rewrite; the browser client owns response-shape normalisation. Fix and test these
  contracts independently.
- **FILE-MCP-001 — MCP browser surfaces.** Cookie-mode Web MCP and API-key MCP are
  distinct endpoints. Browser wrapper responses may differ from raw MCP envelopes;
  authentication and tools/list must be tested with the selected mode.
- **FILE-ROUTE-001 — Canonical entry.** Derive the current SPA entry route and API
  rewrite exceptions from source. Keep jobs/log routes from being captured by broader
  admin/API rewrite rules.
- **FILE-UI-001 — Paired UI source.** Editable source and Playwright live in the
  file-mcp monorepo app; Docker/preprod serve the synced service `ui/dist`. Treat them
  as one delivery surface.
- **FILE-STATE-001 — Database-backed profiles.** Active SQLite profile rows are merged
  into runtime configuration and can override mounted/default settings. Inspect the
  selected profile and use a fresh store for deterministic image smoke.
- **FILE-SQLITE-001 — Schema and cleanup.** Guard updates for schema-versioned columns,
  stop the owning stack before compacting/removing a test database, and never let one
  env-hash runtime contaminate another.
- **FILE-LIFECYCLE-001 — Split and unified modes.** Native validation uses separate role
  processes plus a frontend preview, while the container may use a unified serve process
  and compatibility proxy. Prove the actual selected shape rather than assuming every
  role has a listener.
- **FILE-LOG-001 — Role-specific logging.** Config keys alone do not wire role logs. The
  bootstrap, adapter and observability path must consume the selected role file, and
  every A2A/tool mutation must emit correlated target-aware audit data.
- **FILE-DOWNLOAD-001 — Download contract.** The browser can implement download through
  the file-read tool and a client blob. Do not invent a backend download endpoint
  without a requirement and source proof.
- **FILE-A2A-001 — A2A input.** Validate A2A tool payloads against the current handler
  contract; the file-write handler may use a compact text format rather than the MCP
  JSON argument shape.
- **FILE-HEALTH-001 — Health and status.** Health proves the expected route surface is
  mounted; status proves runtime metrics/data. A working status with missing health
  often indicates a mixed-role stack.
- **FILE-ENV-001 — Complete env surface.** Container smoke needs the complete current
  environment/defaults contract. A partial hand-built env can fail on unresolved
  placeholders and is not image evidence.
- **FILE-UI-002 — Shared UI patterns.** Verify current shared SearchPanel, table and
  console behaviour before preserving an old bespoke-UI gap. Shared selection cells can
  change accessible names and locator uniqueness.

## Historical provenance

The complete pre-refresh document is preserved at commit `a9c00dc49ff7419d5ea5f7cd1ab117096e266ff6`, path `AGENT-LESSONS.md`, SHA-256 `5fc2b2e7f5a483ce3a29bfbbd43e401b4ff97483511fdefbe37f1e0f6df202e9`. Its 123 addressable units, including 29 historical, mutable, duplicate or heading-only units omitted from the active body, are mapped individually in the central `lesson-unit-migration.tsv` ledger.
