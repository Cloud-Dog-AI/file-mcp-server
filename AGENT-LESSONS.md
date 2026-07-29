# file-mcp-server — Local Agent Lessons

> **Common authority:** Read [Platform Rules](../cloud-dog-ai-platform-standards/RULES.md) and [Platform Lessons](../cloud-dog-ai-platform-standards/AGENT-LESSONS.md) first. This file adds local facts only; it cannot weaken common policy.

Platform Standards owns common policy. This overlay owns File-MCP facts only.

- Exercise real scoped file operations through API, MCP, A2A and WebUI; prove
  authorised read/write and forbidden cross-scope/no-auth paths.
- Keep backend/profile, storage-path and credential facts in current configuration;
  never copy them into lessons or evidence.
- Prove storage persistence and audit records with the selected real backend, not
  a mock or health route.

- Trace the selected profile through UI state, request headers, authentication, tool registry and backend selection; HTTP/profile protection and file-tool permission are separate checks.
- Derive SPA entry, API rewrite and jobs/log route exceptions from current source; keep the paired UI source and exact synced `ui/dist` bundle together for delivery proof.
- Active SQLite profile rows can override defaults: inspect the selected profile, isolate test stores and never let one environment/hash runtime contaminate another.
- Validate A2A payloads against the actual handler contract; do not assume they use the MCP argument shape.

Evidence: current backend config; scoped-operation matrix; audit/persistence
readback; local and PREPROD Playwright reports.

- **Listener ports.** API `8060`, Web `8061`, MCP `8062` and A2A `8063` are this service's default listener allocation. Read current `defaults.yaml` and the authorised environment overlay before use; never use the retired bootstrap table or guess an override.
