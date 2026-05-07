# W28A-86 File MCP Vault Bootstrap Env Carve-Out Report

Date: 2026-05-07

## Reading Proof

- Dispatch read: `W28A-86-FILE-MCP-DEEP-REFACTOR-2026-05-07.md`.
- Platform bootstrap read: file-mcp service root and ports are `file-mcp-server` on `8060/8061/8062/8063`.
- RULES §1.4 read: `cloud_dog_config` is mandatory; bespoke config loaders, Vault resolvers, env parsers, and fallback chains are forbidden.
- RULES §5.6 read: `env-vault` delivers `VAULT_ADDR`, `VAULT_TOKEN`, `VAULT_MOUNT_POINT`, and `VAULT_CONFIG_PATH` through the process environment for Vault bootstrap.
- Platform lessons read: Vault is optional but `cloud_dog_config` is mandatory; do not write fallback chains.
- File-mcp lessons read: for this repo, pytest commands require `--env`; local WebUI validation uses ports `8060-8063`.
- Audit #94 read: only two file-mcp findings were `VAULT_MOUNT_POINT` and `VAULT_CONFIG_PATH` in `src/file_tools/config/adapter.py`.

## Change

- Confirmed `VAULT_MOUNT_POINT` and `VAULT_CONFIG_PATH` are bootstrap inputs needed to configure the Vault connection before Vault-backed config values can be resolved.
- Kept the four existing bootstrap reads in `src/file_tools/config/adapter.py`.
- Updated comments in `src/file_tools/config/adapter.py` and `src/file_tools/observability.py` so the required audit grep is not tripped by comment-only `os.environ` text.
- No runtime config logic was changed.

## Audit

Command:

```bash
grep -rn "os\.environ" src/ --include="*.py" | grep -v __pycache__ | grep -v "VAULT_ADDR\|VAULT_TOKEN\|VAULT_MOUNT_POINT\|VAULT_CONFIG_PATH"
```

Result: zero matches.

Raw direct environment reads remaining:

- `VAULT_ADDR`
- `VAULT_TOKEN`
- `VAULT_MOUNT_POINT`
- `VAULT_CONFIG_PATH`

These are all in `src/file_tools/config/adapter.py` and are the documented Vault bootstrap carve-out.

Evidence: `working/audit-86.log`

## Verification

- Unit: `182 passed, 1 warning in 22.74s`
- System: `30 passed in 80.63s`
- Integration: `47 passed, 1 skipped in 429.52s`
- Application rerun: `25 passed, 1 skipped in 149.65s`

Logs:

- `working/ut-86.log`
- `working/st-86.log`
- `working/it-86.log`
- `working/at-86-rerun.log`

Initial AT attempt: `working/at-86.log` produced `14 passed, 1 skipped, 11 errors` because the local WebUI stack was incomplete: `8061` was serving the SPA but `8060` API was not listening, causing `/auth/login` to return `502 API unreachable`. Starting the missing API role with `tests/env-AT` resolved the environment issue; the rerun passed.

Temporary API role cleanup:

- Start evidence: `working/start-api-86.log`
- Stop evidence: `working/stop-api-86.log`

## Closing Warrant

- `cloud_dog_config` remains the config/Vault resolution path.
- No bespoke Vault resolver or env fallback chain was added.
- Required §1.4 service grep excluding the documented Vault bootstrap names returns zero.
- UT/ST/IT/AT verification completed with passing rerun evidence.
