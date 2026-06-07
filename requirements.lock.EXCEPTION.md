# requirements.lock — exception (W28A-861-R3)

A fully-resolved public-boundary `requirements.lock` cannot be produced for
`file-mcp-server` at this time. The blocker is recorded here per §6 of
`W28A-861-R3-PUBLICATION-PREP-EXTERNAL-BUILD-LEAKAGE-HARDENING-2026-06-07.md`
(record the exact command + error; do not silently omit).

## Why

The service depends on seven Cloud-Dog platform packages
(`cloud_dog_config`, `cloud_dog_logging`, `cloud_dog_api_kit`,
`cloud_dog_idam`, `cloud_dog_db`, `cloud_dog_jobs`, `cloud_dog_storage`).
These are **not yet published to the public index (pypi.org)**. The §4 package
strategy for the public boundary is single-index `https://pypi.org/simple` with
**no** `--extra-index-url` (PS-97 §3.3). A lock that pins exact transitive
versions therefore cannot be resolved on the public boundary until the platform
packages are published there (handoff to the publication-loop lane
W28A-862-R3 / W28A-865).

Producing a lock against the internal Gitea index instead would bake an
internal-host reference into a publishable artefact, which §5 forbids. So a
lock is deliberately NOT committed rather than committing an internal-host lock.

## Exact command attempted

```
pip-compile --index-url https://pypi.org/simple --no-emit-index-url \
  --strip-extras --output-file requirements.lock REQUIREMENTS.txt
```

(pip-tools 7.5.3, pip resolver, single public index, no extra-index-url.)

## Exact error

```
ERROR: Could not find a version that satisfies the requirement
  cloud_dog_config>=0.3.1 (from versions: none)
pip._vendor.resolvelib.resolvers.exceptions.RequirementsConflicted:
  Requirements conflict: SpecifierRequirement('cloud_dog_config>=0.3.1')
pip._vendor.resolvelib.resolvers.exceptions.ResolutionImpossible:
  [RequirementInformation(requirement=SpecifierRequirement('cloud_dog_config>=0.3.1'), parent=None)]
pip._internal.exceptions.DistributionNotFound:
  No matching distribution found for cloud_dog_config>=0.3.1
```

The same failure applies to the other six `cloud_dog_*` packages.

## Reproducibility in the interim

Until the platform packages reach pypi.org, reproducibility is anchored by:

- `REQUIREMENTS.txt` — pinned ranges for all third-party deps (lower bound +
  major-version upper bound on every pinnable package).
- `pyproject.toml` `[project].dependencies` — must stay consistent with
  `REQUIREMENTS.txt` (the public Dockerfile installs the `cloud_dog_*` packages
  by name and the rest from `REQUIREMENTS.txt`).
- `Dockerfile.public` pins `cloud-dog-api-kit==0.12.4` exactly (the one
  version-sensitive platform package).

## Removal condition

Replace this file with a real `requirements.lock` once the seven `cloud_dog_*`
packages are published to `https://pypi.org/simple` (Cloud-Dog-External
namespace). At that point re-run the exact command above; it will resolve, and
`requirements.lock` becomes the committed artefact.
