# W28A-148A-R1 File MCP Packaged UI Deploy Closeout

Date: 2026-05-11

## Scope

Closed the W28A-148A packaged UI deploy blocker for `filemcpserver0` only.

Guardrails followed:

- No LLM, Ragflow, embedding, translation, or generation flows were run.
- No full W28A-102 estate rerun was run.
- No public package publication was run.
- Terraform deployment was targeted only to `docker_image.filemcpserver` and `docker_container.filemcpserver0`.
- `cloud-dog-ai-ui-monorepo/apps/file-mcp/**` was used only for direct-preprod verification.

## Starting State

- `file-mcp-server` was clean at `ac4619d fix(file-mcp): sync W102 packaged ui`.
- `cloud-dog-ai-ui-monorepo` was at `fa70d3d fix(file-mcp): close W102 rendered e2e failures`; unrelated dirty files existed outside `apps/file-mcp` before this closeout.
- Live direct preprod was still serving old UI bundle `/assets/index-10fywsPP.js`.
- `https://filemcpserver0.cloud-dog.net/health` returned `status=ok`, `readiness=ok`.

## Packaged UI Proof

Packaged UI asset in `file-mcp-server/ui/dist`:

- `ui/dist/index.html` references `/assets/index-CrXlvLXG.js` and `/assets/index-GZo4-FXb.css`.
- `ui/dist/assets/index-CrXlvLXG.js` contains the W28A-148A markers:
  - `Connection test running`
  - `Job detail`
  - `read_file`
  - `workspace`

After deployment, live preprod served:

- `/assets/index-CrXlvLXG.js`
- `/assets/index-GZo4-FXb.css`

Live JS hash proof:

- `/tmp/filemcp-live-CrXlvLXG.js`: `4aa0e3dcf4cb8bcd0cc843938a1461e4ce86d35e8c7d1537709c551dd81a3a3a`
- `ui/dist/assets/index-CrXlvLXG.js`: `4aa0e3dcf4cb8bcd0cc843938a1461e4ce86d35e8c7d1537709c551dd81a3a3a`

## Build, Push, Deploy Proof

Build command:

```bash
./docker-build.sh latest
```

Result:

- Build passed.
- Local image/config ID: `sha256:aaf3cb50ceae530bf773b712fd1e37c98fc7498ce1ee15eb4514fd3ca96a7018`
- Image created: `2026-05-11T16:34:50.557983149+01:00`

Push command:

```bash
docker push registry.cloud-dog.net:443/cloud-dog/file-mcp-server:latest
```

Result:

- Pushed manifest digest: `sha256:4af93d27a34a4c7a9a47b0fa357ba85155753cb0fc90448433eea6c847a1c4fb`
- Registry header `Docker-Content-Digest`: `sha256:4af93d27a34a4c7a9a47b0fa357ba85155753cb0fc90448433eea6c847a1c4fb`
- Repo digest after push: `registry.cloud-dog.net:443/cloud-dog/file-mcp-server@sha256:4af93d27a34a4c7a9a47b0fa357ba85155753cb0fc90448433eea6c847a1c4fb`

Terraform workspace:

```text
/opt/iac/cloud-dog-repo/terraform/server0.viewdeck.com/27 MLAgents
```

Plan command:

```bash
terraform plan -out=W28A-148A-R1-filemcp.tfplan -target=docker_image.filemcpserver -target=docker_container.filemcpserver0 -replace=docker_container.filemcpserver0
```

Plan result:

- `Plan: 2 to add, 0 to change, 2 to destroy.`
- Targeted resources only:
  - `docker_image.filemcpserver`
  - `docker_container.filemcpserver0`

Apply command:

```bash
terraform apply -input=false W28A-148A-R1-filemcp.tfplan
```

Apply result:

- `Apply complete! Resources: 2 added, 0 changed, 2 destroyed.`

Runtime proof:

- Container: `filemcpserver0.app.vpc0.cloud-dog.net`
- Container ID: `cb8db4ee0d381bb47eb66516b945868aab17c0e59c61068f7b97ed829354eaa5`
- Runtime image/config ID: `sha256:aaf3cb50ceae530bf773b712fd1e37c98fc7498ce1ee15eb4514fd3ca96a7018`
- Runtime status: `running`
- Runtime health: `healthy`
- Container created: `2026-05-11T15:35:51.371340593Z`
- Terraform state `pull_triggers`: `sha256:4af93d27a34a4c7a9a47b0fa357ba85155753cb0fc90448433eea6c847a1c4fb`
- Terraform state `repo_digest`: `registry.cloud-dog.net:443/cloud-dog/file-mcp-server@sha256:4af93d27a34a4c7a9a47b0fa357ba85155753cb0fc90448433eea6c847a1c4fb`

Post-deploy health:

- `https://filemcpserver0.cloud-dog.net/health`
- Result: `status=ok`, `readiness=ok`, service `file-mcp-server`, version `0.1.2RC1`.

## Direct Preprod Verification

Focused W28A-148A direct-preprod rerun:

```bash
E2E_BASE_URL=https://filemcpserver0.cloud-dog.net E2E_USE_LOCAL_SERVER=0 E2E_API_BASE_URL=https://filemcpserver0.cloud-dog.net/api E2E_API_KEY=<redacted> npx --no-install playwright test tests/e2e/audit-log.spec.ts tests/e2e/ui-review2.spec.ts tests/e2e/W28A-119A-rendered-assertions.spec.ts --grep 'view, filter and export audit log|T23 AuditLog|W28A-119A' --reporter=list --workers=1
```

Result:

- `5 passed (15.0s)`

Passing tests:

- `tests/e2e/audit-log.spec.ts:52` - `view, filter and export audit log`
- `tests/e2e/ui-review2.spec.ts:334` - `T23 AuditLog - DataTable has sort, page jump, RelativeTime`
- `tests/e2e/W28A-119A-rendered-assertions.spec.ts:78` - `W28A-119A file browser renders type icons, metadata, tree expansion, and selected preview`
- `tests/e2e/W28A-119A-rendered-assertions.spec.ts:147` - `W28A-119A search term error renders deterministic preview and opens the result`
- `tests/e2e/W28A-119A-rendered-assertions.spec.ts:180` - `W28A-119A storage profile connection test renders an inline row status`

Full File MCP W28A-102 direct-preprod shard:

```bash
E2E_BASE_URL=https://filemcpserver0.cloud-dog.net E2E_USE_LOCAL_SERVER=0 E2E_API_BASE_URL=https://filemcpserver0.cloud-dog.net/api E2E_API_KEY=<redacted> npx --no-install playwright test --reporter=list --workers=1
```

Result:

- `62 passed (2.2m)`

## Repo And Artifact Notes

Committed source change intended by this closeout:

- `file-mcp-server/working/W28A-148A-R1-FILE-MCP-PACKAGED-UI-DEPLOY-CLOSEOUT.md`

Verification side effects not committed:

- Playwright verification updated four screenshot files under `cloud-dog-ai-ui-monorepo/apps/file-mcp/screenshots/`.
- Terraform left an untracked saved plan in the deployment workspace: `W28A-148A-R1-filemcp.tfplan`.
- Existing unrelated dirty files in `cloud-dog-repo` and `cloud-dog-ai-ui-monorepo` were not touched or reverted.

## Residual Blockers

No File MCP W28A-148A packaged UI or direct-preprod W28A-102 shard blocker remains.

Residual hygiene only:

- The UI monorepo has verification-generated screenshot modifications under `apps/file-mcp/screenshots/`; not committed because the UI repo was verification-only for this closeout.
- The deployment workspace has an untracked saved Terraform plan file from this deploy plus unrelated pre-existing dirty/untracked files; not committed here.
