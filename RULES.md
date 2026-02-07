# File MCP Server

# AI ASSISTANT RULES - ABSOLUTE COMPLIANCE REQUIRED

## ⚠️ CRITICAL: ABSOLUTE HONESTY AND INTEGRITY ⚠️

**I WILL NEVER:**
- **LIE** about test results, implementation status, or compliance
- **FUDGE** test data, configuration, or validation results
- **HACK** around problems instead of fixing root causes
- **FALSIFY** test outputs, logs, or status reports
- **STUB** functionality in Integration/Application tests when real implementation is required
- **FAKE** success when there are errors, warnings, or failures
- **HIDE** failures, warnings, or non-compliance
- **PRETEND** tests pass when they fail
- **SKIP** validation steps to claim completion
- **BYPASS** rules or requirements for convenience

**IF I CANNOT GUARANTEE 100% COMPLIANCE, I WILL STOP AND SAY SO EXPLICITLY.**

**IF TESTS FAIL, I WILL REPORT FAILURES HONESTLY, NOT HIDE THEM.**

**IF I DON'T KNOW, I WILL ASK, NOT GUESS.**

---

## SCOPE BOUNDARIES (PROJECT-SPECIFIC)

- **No LLM integration.** The service is file tooling only.
- **No network crawling or internet search.** Operate only within configured filesystem scope.
- **No out-of-scope features** beyond the defined tool catalogue, validation, audit, snapshots, and conversion pipeline.

---

## CONFIGURATION & ENVIRONMENT SETTINGS (ZERO TOLERANCE)

### Configuration Precedence (highest to lowest)
1. `os.environ`
2. **Env file** (`.env` or `--env private/env-<name>` when supported by tooling)
3. `config.yaml`
4. `defaults.yaml`

### Absolute Rules
- **NEVER** hardcode URLs, ports, paths, API keys, allowed extensions, scope roots, or tool defaults.
- **ALL** configuration must come from the precedence chain above.
- **ALL secrets/credentials** live in `private/env-*` or `.env` (ignored by git).
- **NEVER** commit credentials to the repo.
- If a script expects `--env`, **ALWAYS** use `--env private/env-<name>`.
- If the config loader does not support `--env`, **ASK** before adding or changing the interface.

### Required Validation
- Config loading must **fail fast** if required settings are missing.
- Any change to config loading must preserve the full precedence chain.

---

## TESTING REQUIREMENTS (REAL SYSTEMS ONLY)

### Absolute Testing Standards
**EVERY TEST MUST:**
1. **Use 100% REAL SYSTEMS**
   - Real filesystem operations (no fake file tools in IT/AT tests)
   - Real validators, audit logging, snapshots, and conversion backends where required
   - **Unit tests may use temp directories**, but must still exercise real code paths

2. **Have ZERO Hardcoded Values**
   - **ALL** values from config precedence chain
   - **ZERO** hardcoded paths, scope roots, extensions, or conversion settings
   - Tests MUST fail clearly if required config/env is missing

3. **Validate 100% of Outputs (Forensic Level)**
   - **Structure**: Keys present, correct types, not null
   - **Format**: JSON/YAML/XML/HTML validity, timestamps, identifiers
   - **Content**: Correct data, correct diffs, correct audit output
   - **Quality**: No hardcoded values leaked, no sensitive data

4. **Test ALL Paths**
   - Success paths, failure paths, edge cases, alternative configurations

5. **Run Tests Properly**
   - Run tests **one at a time** when diagnosing issues
   - Monitor output in real time; stop on errors or warnings

6. **Report Honestly**
   - Summarize test status (PASS/FAIL)
   - Update `docs/TESTS.md` when tests are executed
   - **NEVER** claim success with failures

---

## MUST NOT DO (ABSOLUTE PROHIBITIONS)

1. **NEVER modify live/production environments** unless explicitly instructed
2. **NEVER modify Docker instances** unless explicitly instructed
3. **NEVER change code without explicit feature/design approval**
   - Provide plan + testing plan first
   - Once a feature/design is approved, proceed with iterative edits without repeated approval for minor tweaks
4. **NEVER bypass scope policy** or operate outside configured roots
5. **NEVER edit audit logs or snapshots directly**
   - Use tool operations; audit logs are append-only
6. **NEVER hardcode configuration values** (CRITICAL)
7. **NEVER fake tests or outputs** (CRITICAL)
8. **NEVER start/stop servers with direct process commands**
   - Use project scripts (e.g., `server_control.sh`) if present
   - If unclear, **ASK** for the correct procedure

---

## MUST DO (ABSOLUTE REQUIREMENTS)

1. **ALWAYS fix and validate locally first**
2. **ALWAYS show a plan before changes** (include testing plan)
3. **ALWAYS verify fixes**
   - Syntax check: `python3 -m py_compile <file.py>`
   - Import check: `python3 -c "import <module>"`
   - Run relevant tests
4. **ALWAYS ask for clarification** when unsure
5. **ALWAYS stop immediately** when told to stop

---

## REPOSITORY STRUCTURE (ALIGNMENT REQUIRED)

The project MUST align to the standard repository layout used by sibling MCP servers:

```
<root>
  README.md
  LICENSE
  RULES.md
  CONTEXT-SUMMARY.md
  REQUIREMENTS.txt
  defaults.yaml
  config.yaml (optional, ignored by git)
  .env (optional, ignored by git)
  openapi.json (if API server exists)
  docker files/scripts, server_control.sh (if server management exists)
  docs/
  src/
  tests/
  scripts/
  logs/
  database/
  private/
  archive/
  working/
  storage/
  tmp/
```

### Folder Purpose
- **docs/**: production documentation only (ARCHITECTURE, REQUIREMENTS, TASKS, TESTS, PARAMETERS, etc.)
- **src/**: all production code
- **tests/**: tests structured and numbered (UT/ST/IT/AT) aligned to `docs/TESTS.md`
- **private/**: credentials and environment files (excluded from git)
- **working/**: transient outputs (excluded from git); harvest valuable info into docs
- **archive/**: retired materials (excluded from git)
- **storage/**: runtime storage (excluded from git)

This structure must be maintained at all times.

---

## DOCUMENTATION ALIGNMENT (REQUIREMENTS → TASKS → TESTS)

Every requirement in `docs/REQUIREMENTS.md` MUST map to:
1. **At least one Task** in `docs/TASKS.md`
2. **At least one Test** in `docs/TESTS.md`

If a requirement lacks a task or test, add it to the backlog immediately.

---

## CODE QUALITY AND HEADER STANDARDS

All source code files must include a header block with:
- License, ownership, description
- Related Requirements, Tasks, Architecture, Tests
- Recent change history (max 10)

Use docstrings for Python and appropriate comment syntax for other languages.

---

## WHEN IN DOUBT

**ASK. DON'T GUESS. DON'T LIE. DON'T FUDGE.**

**If I cannot guarantee 100% compliance, I STOP and say so.**

---

*Last updated: 5 February 2026*
