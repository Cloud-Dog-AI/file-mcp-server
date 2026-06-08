# W28A-861-R3 — file-mcp public-build prep (service report)

Service: file-mcp-server
Worktree: /opt/iac/Development/cloud-dog-ai/.w28a861r3-file-mcp
Branch: fix/W28A-861-R3-file-mcp (off origin/main @ ba0089b)

## Mandatory reading (versions cited)

- RULES.md v2.7 (platform-standards) — §3.2.0 Gitea exclusivity, §7 no-SSH
  (docker -H tcp:// only).
- AGENT-LESSONS.md v3.17 (2026-06-07) — §6.13 isolated worktree per lane;
  §6.92/§6.93 auditor coverage; "pre-existing not escape hatch".
- AGENT-BOOTSTRAP-DIRECTIVE.md — bootstrap/seed conventions.
- PLATFORM-TLS-PROXY-GUIDANCE.md — public build uses system trust store, no
  private CA overlay.
- docs/standards/97-gitea-github-isolation.md (PS-97 v1.1, 2026-04-23) —
  §1.1.3 Dockerfile split, §1.1.4 env split, §3.3 single index / no
  extra-index-url, §4 anti-patterns.
- working/instructions/W28A-861-R3-...-2026-06-07.md — §4 package decision,
  9-step required work.

## §4 decision implemented

Public boundary = `https://pypi.org/simple` (single index) + GitHub-mirrored /
public-PyPI platform packages. Gitea (`pypi.cloud-dog.net` / gitea mirror) is
the dev/internal variant default only. Index supplied via build ARG
(`PYPI_INDEX_URL`, default pypi.org). No hardcoded internal host on the public
path. No `--extra-index-url` on the public path (PS-97 §3.3).

## Ports + prefix DERIVED (source)

- Unified HTTP surface: 8080
  - source: `env-docker-defaults:20` (FILE_MCP_HTTP_PORT=8080),
    `Dockerfile` EXPOSE 8080, `PUBLICATION-SMOKE.md` probes 8080,
    `defaults.yaml:118-127` http block, `scripts/port-proxy.py:13`
    (MAIN_PORT defaults to CLOUD_DOG__WEB_SERVER__PORT=8080).
- PS-92 compatibility ports proxied to 8080:
  - MCP 8081 (scripts/port-proxy.py:15 default CLOUD_DOG__MCP_SERVER__PORT)
  - API 8083 (scripts/port-proxy.py:14 default CLOUD_DOG__API_SERVER__PORT)
  - port-proxy started by docker-entrypoint.sh; only 8080 is externally needed.
- Env prefix: `FILE_MCP_` (env-docker-defaults, docker-env.example) plus PS-92
  `CLOUD_DOG__*` port keys (defaults.yaml:133-156).
- Install method DERIVED from existing Dockerfile: direct package list
  (`cloud-dog-*` by name) + `REQUIREMENTS.txt` minus `cloud_dog_` lines +
  `redis>=5.0`. Replicated in Dockerfile.public.

## Files produced/changed (1 line each)

- Dockerfile.public (new) — public variant; direct-install method; single
  `--index-url ${PYPI_INDEX_URL}` (pypi.org default); no extra-index-url;
  non-root appuser; EXPOSE 8080; COPYs docker-env.public.example as the env.
- docker-env.public.example (new) — public *.example.com placeholders,
  `<your-...-here>` tokens, 8080 + PS-92 ports.
- EXTERNAL-BUILD.md (new) — self-contained external builder doc; Linux/macOS/
  Windows; Docker + pure-source paths; ports table; evidence/tarball return.
- requirements.lock.EXCEPTION.md (new) — exact pip-compile cmd + error;
  blocker is platform pkgs absent on pypi.org; removal condition stated.
- docker-build.sh (mod) — `--variant public|dev`; public→pypi.org single index
  (no extra-index-url), dev→gitea mirror; PYPI_INDEX_URL build arg; variant-aware
  registry tagging.
- README.md (mod) — public package source pypi.org; `--index-url`; link to
  EXTERNAL-BUILD.md.
- BUILD.md (mod) — public/dev variant build commands; single-index install.
- docker-config.profiles.example.yaml (mod) — removed `${vault.dev.storage.*}`
  prefixes; kept env-var form.
- env-docker-example (mod) — vault paths → `<your-...-here>` placeholders.
- docs/ENV-REFERENCE.md, docs/PARAMETERS.md (mod) — vault-path default cells →
  env-var form.
- .publish-exclude (mod) — exclude migration/, tests/, AGENT-LESSONS.md,
  RULES.md, docker-build.log from public mirror (§9 internal scaffolding).
- .gitignore (mod) — ignore .pip.conf.build / .ca-bundle.build build secrets.

## Leakage scan BEFORE / AFTER

BEFORE (publishable tree, tracked, minus internal-only files):
8 files with internal-host / vault-path leaks:
  BUILD.md, README.md (gitea "public source" + --extra-index-url);
  docker-config.profiles.example.yaml, env-docker-example,
  docs/ENV-REFERENCE.md, docs/PARAMETERS.md (${vault.dev.storage.*});
  Dockerfile, docker-build.sh (gitea default — dev path).

AFTER (public boundary file set actually shipped by Dockerfile.public):
0 actual leaks. Residual pattern hits are all intentional/non-leaks:
  - Dockerfile / docker-build.sh dev-variant gitea default (gated by
    --variant dev; legitimate internal-build default per Gitea-build-stage rule);
  - docs/REQUIREMENTS.md `${vault.*}` = capability description, not a path;
  - EXTERNAL-BUILD.md / Dockerfile.public / requirements.lock.EXCEPTION.md
    prose that names the prohibited tokens to forbid them;
  - .publish-exclude comment naming excluded scaffolding.

## Lockfile status

EXCEPTION (requirements.lock.EXCEPTION.md). pip-compile against pypi.org fails:
`No matching distribution found for cloud_dog_config>=0.3.1` (the 7 cloud_dog_*
platform packages are not on the public index). Real lock blocked on the
package-publish handoff to W28A-862-R3 / W28A-865.

## Build attempt (honest)

server2 (DOCKER_HOST=tcp://server2.viewdeck.com:2375, docker 28.3.3),
`./docker-build.sh latest --variant public`:
  - apt + COPY stages succeeded;
  - pip step ran with single `--index-url https://pypi.org/simple`
    (NO --extra-index-url — proves §4/PS-97 §3.3 compliance);
  - FAILED at `cloud-dog-config` not on pypi.org (exit 1) — the documented §4
    gap, identical to the lockfile blocker.
`docker buildx build --call=check -f Dockerfile.public`: "Check complete, no
warnings found." No leftover image on server2.
py_compile: src/**/*.py + scripts/port-proxy.py all compile (exit 0).

## Blockers (concrete owner)

- Platform packages (cloud_dog_config/logging/api_kit/idam/db/jobs/storage) not
  on the public index (pypi.org). Owner: publication-loop lane W28A-862-R3 /
  W28A-865. Until published, the public Dockerfile + requirements.lock cannot
  complete end-to-end. Mechanics are proven correct; only the upstream publish
  is outstanding.
