# W28A-148A File MCP W102 E2E Return

Date: 2026-05-11

## Scope

Owned paths only:

- `cloud-dog-ai-ui-monorepo/apps/file-mcp/**`
- `file-mcp-server/**`

No LLM, Ragflow, Docker, Terraform, or service redeploy was run. Validation used the rebuilt local File MCP UI with Vite same-origin proxy to the accepted preprod host `https://filemcpserver0.cloud-dog.net`.

## Findings And Fixes

- Audit seed/direct MCP failures did not reproduce on the first focused preprod rerun. `audit-log.spec.ts:52` and `ui-review2.spec.ts:334` passed against direct remote preprod before code changes.
- The W28A-119A tree assertion used `/^(workspace|root)$/i`, but the preprod DOM legitimately contained both the logical workspace root and a child directory named `root`. The test now selects `workspace` exactly, falling back to `root` only when no workspace root exists.
- The packaged File MCP UI bundle was stale: current source already unwraps `read_file` payloads with `value`, but `file-mcp-server/ui/dist` still rendered JSON-wrapped previews. Rebuilt and synced the packaged UI bundle.
- Deleting a file opened from Search left the `file` query parameter in place, causing File Browser to reopen the deleted path and render a not-found JSON preview. Delete now clears the file query by replacing search params with the current directory path.
- Storage profile Test connection had no immediate inline row feedback while `backend_status` was pending. The row now renders a `Connection test running ...` status immediately and then updates to pass/warning/failure.
- Full-shard rerun exposed two adjacent blockers: page-level create status made profile connection status ambiguous, and Jobs Detail waited for `/jobs/{id}` before opening. The profile page now clears page-level status before row status; Jobs opens detail immediately from row summary and hydrates asynchronously. The dialog title now starts with `Job detail` for the accessible name contract.

## Validation

Focused direct remote preprod reproduction before fixes:

- Command shape: `E2E_BASE_URL=https://filemcpserver0.cloud-dog.net E2E_USE_LOCAL_SERVER=0 E2E_API_BASE_URL=https://filemcpserver0.cloud-dog.net/api npx --no-install playwright test <five W28A-102 specs> --reporter=list --workers=1`
- Result: `2 passed, 3 failed`.
- Passing: audit log seed spec; UI review T23 audit seed spec.
- Failing: W28A-119A tree ambiguity; JSON-wrapped preview; storage profile inline status.

Focused rebuilt UI with preprod API proxy:

- Result: `5 passed (15.1s)`.

Additional blocker reruns:

- `profiles.spec.ts` connection profile test: passed.
- W28A-117 jobs detail test: `1 passed (3.9s)`.

Full File MCP W28A-102 shard, rebuilt UI with preprod API proxy:

- Result: `62 passed (2.2m)`.

## Residual Blockers

- Direct remote-preprod UI still serves the previously deployed bundle until the packaged File MCP UI is deployed. This return did not run Docker, Terraform, or redeploy by instruction.
- No backend/API blocker remains from the focused File MCP failures.
