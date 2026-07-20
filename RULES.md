# file-mcp-server — Local Rules

## Common contract — binding

Read [the platform RULES](../cloud-dog-ai-platform-standards/RULES.md) and
`AGENT-LESSONS.md` in full before work. This overlay adds file-service safeguards
only; central Gate 0, build and preprod controls remain binding.

## Local rules

- Restrict every operation to the authorised profile/root and enforce canonical path,
  traversal, symlink, file-type and size policy at the tool boundary. This service is
  not a crawler or arbitrary host-filesystem interface.
- Profile selection propagates through UI, headers, identity, registry and backend.
  HTTP admin/profile permissions and tool read/write permission are separate and both
  need direct proof.
- File mutations, snapshots and audit records use the supported service/storage path;
  never edit audit/snapshot/cache/database state to manufacture lifecycle proof.
- Preserve split-role versus unified-container semantics from the selected runtime;
  derive listeners, health/status, routes and logs from current source/configuration.
- Build the paired monorepo UI and prove the exact `ui/dist` distribution, browser
  flow, download behaviour and A2A payload contract actually served by the image.

Historical paths, ports, package pins and incident metrics are retired to Git history.
