---
template-id: T-TPR
template-version: 1.0
applies-to: tests/fixtures/TEST-PACK-REFERENCE.md
project: file-mcp-server
doc-last-updated: 2026-06-23T14:02:08Z
doc-age-policy: 90d
---

# file-mcp-server — Test-Pack Reference

> Generated for W28E-1802A from `cloud-dog-ai-platform-standards/test-packs/REGISTRY.tsv`
> per PS-TEST-PACKS-REGISTRY. This file references central pack IDs, source zips, and
> SHA256 values; it does not copy unpacked dump contents.

## 1. Service-specific pack

`file-mcp-server` has **no service-specific test pack** registered in
`test-packs/REGISTRY.tsv` (no `owner_service: file-mcp-server` row). file-mcp is a mature service
whose test catalogue (388 functions across 117 modules under `tests/`) is authored in-repo and
bound to requirements via `@pytest.mark.req(...)`; there is therefore no external service zip to
consume.

## 2. Shared / cross-service packs consumed

`file-mcp-server` is in scope for the programme-wide packs whose `applies_to_services` is `all`:

| pack_id | pack_kind | source_zip (relative to platform-standards) | sha256 | size_bytes | stream_binding |
|---|---|---|---|---|---|
| `TP-COMMON` | shared | `working/evidence/W28C-1711-KNOWLEDGE-FILES/INBOX-ARCHIVE/Test-Design-Audit-Jun26-2026-06-16/common-test-suite.zip` | `3af79a7b19fcd3d4161ad9bff8b79f3fa6dce07e4c8ebf9de74058fd5511c754` | 6598 | A/B/C |
| `TP-INTEGRATION-EXAMPLES` | cross-service | `working/evidence/W28C-1711-KNOWLEDGE-FILES/INBOX-ARCHIVE/Test-Design-Audit-Jun26-2026-06-16/integration-examples-test-suite.zip` | `50f8aa7463c83635527098ddca8f1f2186085d66cd7516c432aa05052a6d9467` | 11730 | A/B/C |

The `TP-AJOBS` platform pack is **NOT consumed** by file-mcp: its `applies_to_services` names
`notification-agent / expert-agent / code-runner / scheduler` only. file-mcp's managed-jobs cover
(`FR-027`, `FR-029` — conversion / base64-decode-to-file run as managed jobs) is exercised by
in-repo integration tests against `cloud_dog_jobs`.

## 3. Design-seed source

file-mcp-server's Stream-A design seed is
`working/evidence/W28C-1711-KNOWLEDGE-FILES/file-mcp-server-KNOWLEDGE.md` (W28C-1711
knowledge-preservation file). Its Test-Design-Audit-Jun26 SUPPLEMENT
(`filemcpserver/WEBUI-REVIEW.md`, `filemcpserver/E2E file-mcp-server.md`,
`filemcpserver/Create folder - doesnt appear.md`) carried no ticked operator disposition box at
ingest and is treated as deferred WebUI feedback for Stream-C (see `docs/TESTS.md` §3 WebUI
acceptance drive-out), not as new Stream-A requirements.
