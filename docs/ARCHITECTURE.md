# file-mcp-server Architecture

## 1. Overview

`file-mcp-server` is a Python-based, POSIX-friendly service that exposes **file tools** over a language-neutral protocol boundary (MCP/JSON-RPC style). It is designed to be used by agents (or any orchestration layer) as a toolbox for:

- Search within files and directories
- Read / write / move / copy / delete (within configured scope)
- Base64 encode/decode
- Diff generation and optional visual diff via `meld`
- Structured edits for supported file types (md, txt, json, yaml, html, xml)
  - Sed-like edits (regex / range / line-based)
  - Structured CRUD operations using element addressing (JSON/YAML paths, XML/HTML XPath/CSS selectors, Markdown section addressing)
- Syntax/structural validation before and after changes, with configurable error handling
- Audited change logging and optional snapshots/backup automation
- Conversion from common formats (Office, PDF, etc.) into md/txt/json/yaml (best-effort, pluggable)

**Key constraints**
- No LLMs, no model dependencies
- No hard-coded values: all config derived from `os.environ → .env → config.yaml → defaults.yaml`
- Server is separated from tool implementations so tools can be reused in other projects
- Language-neutral interface: clients in any language can call tools consistently

---

## 2. Repository Layout (recommended)

```
repo/
  README.md
  REQUIREMENTS.txt
  ARCHITECTURE.md
  defaults.yaml
  config.yaml                # optional local config (ignored by default in git)
  .env                       # optional local env file (ignored by default in git)
  pyproject.toml             # optional; recommended for packaging + tooling
  src/
    file_tools/              # reusable library (NO server concerns)
      __init__.py
      config/
        __init__.py
        loader.py            # env/.env/yaml config chain + schema
        models.py            # Pydantic models (validated configuration)
      scope/
        __init__.py
        policy.py            # allow/deny rules, filetype restrictions, path normalisation
      audit/
        __init__.py
        logger.py            # append-only audit log + structured events
        snapshots.py         # snapshot/backup manager (copy-on-write / timestamped)
      io/
        __init__.py
        filesystem.py        # atomic write, locking, safe read, move, copy
        encoding.py          # base64 and encoding detection
      search/
        __init__.py
        find.py              # file/contents search
      edit/
        __init__.py
        sedlike.py           # regex, range, line edits (generic text)
        markdown.py          # section addressing and edits for md
        jsonyaml.py          # JSON/YAML CRUD via JSONPath-ish pointers
        xmlhtml.py           # XPath/CSS selector based ops (lxml/bs4)
        patch.py             # unified-diff generation and apply (optional)
      validate/
        __init__.py
        validators.py        # json/yaml/xml/html/md structural checks
      convert/
        __init__.py
        converters.py        # pluggable conversion pipeline
        backends/
          pandoc.py
          libreoffice.py
          pdf.py
      diff/
        __init__.py
        diffgen.py           # textual diff (unified)
        meld.py              # shell-out to `meld` (optional)
      tools/
        __init__.py
        registry.py          # tool registration + schemas
        definitions.py       # tool input/output models
    file_mcp_server/         # server package (thin wrapper)
      __init__.py
      server.py              # transport + request dispatch
      auth.py                # api key validation, key rotation support
      main.py                # entrypoint CLI for running server
  tests/
    unit/
    integration/
```

**Separation rule**
- `file_tools/` contains zero server code and is importable into any other Python project.
- `file_mcp_server/` contains transport, auth, and request routing only.

## 2.1 Current scaffolding status (bootstrap)
- `src/file_mcp_server/main.py` provides a minimal Typer CLI entrypoint (`python -m file_mcp_server --help`).
- `src/file_mcp_server/server.py` and `auth.py` are stubs reserved for transport/auth wiring.
- `src/file_tools/*` packages are created as placeholders for config, scope, audit, IO, search, edit, validate, convert, diff, and tool registry modules.

---

## 3. Configuration and Precedence

### 3.1 Precedence chain
Highest wins:

1. `os.environ`
2. `.env` file (loaded if present; path configurable)
3. `config.yaml` (per-environment configuration; supports multiple named profiles)
4. `defaults.yaml` (baseline defaults)

No hard-coded values in code; code only defines *required keys* and *validation rules*.

### 3.2 Profiles (default, config1, config2, ...)
Config supports multiple profiles, each with:
- `api_key` (or key set)
- `scope` (root directories, allowlist/denylist patterns)
- `allowed_types` (extensions / mime families)
- `read_only_types` (optional)
- `validation_policy` (strict/warn/ignore per filetype)
- `audit_log` path and format
- `snapshot_policy` (on_write, schedule hints, retention)
- `conversion_policy` (enabled backends, temp dirs, max sizes)

### 3.3 Example schema (conceptual)
```yaml
profiles:
  default:
    auth:
      api_keys:
        - "${FILE_MCP_API_KEY}"   # env substitution supported by loader
    scope:
      roots:
        - "/repo"
      deny_globs:
        - "**/.git/**"
        - "**/node_modules/**"
      allow_globs:
        - "**/*"
    file_types:
      allowed_exts: [".md", ".txt", ".json", ".yaml", ".yml", ".html", ".xml", ".pdf", ".docx", ".xlsx"]
      structured_edit_exts: [".md", ".json", ".yaml", ".yml", ".html", ".xml"]
    audit:
      log_path: "/repo/.file-mcp/audit.log.jsonl"
      include_content_hashes: true
    snapshots:
      enabled: true
      mode: "on_change"           # none|on_change|scheduled
      dir: "/repo/.file-mcp/snapshots"
      retention_days: 30
    validation:
      default_mode: "strict"      # strict|warn|ignore
      per_type:
        ".yaml": "strict"
        ".md": "warn"
    conversion:
      enabled: true
      backends: ["pandoc", "libreoffice", "pdfminer"]
      max_input_mb: 25
```

### 3.4 FastMCP deployment configuration (reference)
FastMCP supports a `fastmcp.json` deployment descriptor with three sections:

- `source`: where the server code lives (filesystem path, entrypoint)
- `environment`: python and dependency constraints
- `deployment`: transport/runtime settings (transport, host, port, path, log level, env, cwd, args)

This is separate from this repo’s `defaults.yaml` / `config.yaml` chain, but useful
when running via the FastMCP CLI (`fastmcp run`). Keep in mind that FastMCP’s
deployment `path` defaults to `/mcp/` when using HTTP transport.

---

## 4. Security Model

### 4.1 Authentication
- Every request must include an API key (header/field depending on transport).
- Keys are configured per profile; multiple keys may be allowed for rotation.
- Server never logs raw keys; logs key identifier/hash prefix only.

### 4.2 Authorisation via Scope Policy
All file operations are constrained by:
- Root directories (`scope.roots`)
- Allow globs and deny globs
- Allowed file extensions/types
- Optional read-only types list

Every path is:
- Normalised (`realpath`)
- Checked for traversal outside roots
- Matched against allow/deny patterns
- Rejected if ambiguous or outside scope

### 4.3 Safe Writes
- Use file locking (`filelock`) for writes
- Atomic writes: write to temp file in same directory, fsync, then rename
- Pre-change validation (optional) and post-change validation (configurable)
- Always emit audit event for any mutation attempt (including failures)

---

## 5. Tool Interface (language-neutral)

### 5.1 Protocol boundary
The server exposes a tool catalogue and accepts tool calls with JSON inputs/outputs.

- Requests and responses are JSON-serialisable
- Inputs/outputs validated using Pydantic models
- Errors returned in structured form:
  - `code`, `message`, `details`, `warnings[]`

This enables clients in any language to call tools consistently.

### 5.2 Tool registration
`file_tools.tools.registry` defines:
- Tool name (stable identifier)
- Input schema
- Output schema
- Handler function
- Capability flags (mutating, requires_validation, supports_dry_run, etc.)

The server simply:
1. Authenticates
2. Loads profile config
3. Applies scope policy
4. Dispatches to tool handler
5. Returns result and warnings/errors

---

## 6. Functional Requirements (detailed)

### 6.1 Core file operations
- `read_file(path, encoding_hint?, range?) -> content, metadata`
- `write_file(path, content, create?, overwrite?, dry_run?) -> result`
- `move_file(src, dst, overwrite?, dry_run?) -> result`
- `copy_file(src, dst, overwrite?, dry_run?) -> result`
- `delete_file(path, dry_run?) -> result`
- `list_dir(path, recursive?, filters?) -> entries`

All must enforce scope policy and log mutation attempts.

### 6.2 Search
- `search_files(query, roots?, globs?, regex?, case_sensitive?, max_results?)`
- `search_content(query, roots?, globs?, regex?, context_lines?, max_results?)`

Search should stream/iterate safely for large trees and respect deny rules.

### 6.3 Base64
- `b64_encode(content|bytes, urlsafe?, wrap?)`
- `b64_decode(b64, urlsafe?)`
Optionally support file-based operations: `b64_encode_file(path)`.

### 6.4 Diff and Meld
- `diff_text(a, b, format="unified", context=3) -> diff`
- `diff_files(path_a, path_b, ...) -> diff`
- `meld(path_a, path_b) -> launched(bool), message`
  - Implemented via shell-out to `meld` if available
  - Disabled in headless environments by default unless enabled

### 6.5 Structured edits (supported: md/txt/json/yaml/html/xml)
#### 6.5.1 Sed-like edits (generic text)
- Replace regex
- Insert before/after line
- Delete matching lines
- Replace within line ranges
- Multi-operation transactions (apply N edits atomically)

#### 6.5.2 Structured CRUD operations
**JSON/YAML**
- Addressing: JSON Pointer (`/a/b/0`), plus optional “dot path” (`a.b[0]`)
- Ops: add, update, delete, move, copy, extract, merge
- Optional schema validation (jsonschema for JSON; YAML best-effort)

**XML**
- Addressing: XPath
- Ops: add/update/remove attribute, add/remove element, replace text, extract subtree

**HTML**
- Addressing: CSS selectors (BeautifulSoup) and/or XPath (lxml.html)
- Ops: same as XML where applicable; warn on malformed HTML

**Markdown**
- Addressing:
  - Heading path: `["H1 Title", "H2 Title", "H3 Title"]`
  - Or anchor/slug addressing
- Ops:
  - Replace section content
  - Insert section under heading
  - Extract section
  - Update frontmatter (if present, YAML frontmatter)

#### 6.5.3 Indexing model
For structured formats, “basic element indexes” means:
- Arrays/lists: numeric index
- Objects/maps: key
- XML/HTML: nth-match selection for selectors/XPath

All operations may run in `dry_run` mode producing a preview diff.

### 6.6 Validation / syntactical analysis
Tool: `validate_file(path, mode?) -> valid(bool), errors[], warnings[]`

- JSON: parse + optional jsonschema
- YAML: parse (ruamel or PyYAML)
- XML: parse (lxml) with well-formedness checks
- HTML: parse (bs4/lxml) with warnings (HTML is often “tag soup”)
- Markdown: structural checks:
  - UTF-8 / decoding
  - heading nesting consistency
  - frontmatter parse if present

After any write/edit tool:
- Optionally run pre-validation and always run post-validation (configurable)
- Modes:
  - `strict`: fail mutation if invalid
  - `warn`: allow mutation but return warnings
  - `ignore`: skip validator for that type

### 6.7 Audit logging (append-only)
Every mutating operation emits an audit event (JSONL recommended), including:
- timestamp (UTC ISO8601)
- tool name
- user/profile identifier
- paths (src/dst)
- content hashes (before/after) where applicable
- diff summary (optional)
- validation result
- snapshot reference (if created)
- status: success/failure + error details

### 6.8 Snapshots / backups
Configurable snapshot policy:
- `none`
- `on_change` (before mutation, copy prior version to snapshot store)
- `scheduled` (server hints only; actual scheduling handled externally or via an optional watcher)

Snapshot store:
- Directory structure by date/path
- Retention policy by days and/or max size
- Manifest index for retrieval

### 6.9 Conversion
Tool: `convert_file(input_path, target_format, options?) -> output_path/content, warnings[]`

Targets:
- `md`, `txt`, `json`, `yaml`

Inputs:
- Office (docx/xlsx/pptx): prefer `libreoffice --headless` or `pandoc` where feasible; Python-only fallback for docx/xlsx
- PDF: `pdftotext` (if available) or `pdfminer.six` fallback

Conversion is implemented as a backend pipeline:
1. Detect type (extension/magic)
2. Choose backend based on config availability
3. Run conversion in sandbox temp dir
4. Validate resulting output (if structured)
5. Return output and warnings

---

## 7. Non-Functional Requirements

### 7.1 POSIX compliance & portability
- Use `os.rename` for atomic replace on same filesystem
- Avoid platform-specific paths
- External tools optional and discovered at runtime (`shutil.which`)

### 7.2 Performance
- Stream reads for large files where possible
- Cap maximum file size for in-memory operations (configurable)
- Search uses incremental scanning; optional ripgrep integration could be added later as a backend

### 7.3 Reliability
- File lock on writes
- Transaction-style multi-edit operations:
  - compute changes
  - validate
  - snapshot
  - atomic write
  - post-validate
  - audit

### 7.4 Observability
- Audit log (append-only)
- Server log for operational messages (separate from audit)
- Optional metrics hooks (no hard dependency)

---

## 8. Key Components and Responsibilities

### 8.1 `file_tools.config`
- Loads and merges configs using precedence chain
- Validates configuration schema
- Performs environment variable expansion

### 8.2 `file_tools.scope`
- Enforces root containment and glob allow/deny
- Determines permitted operations by extension/type
- Exposes `ScopePolicy.check(path, op_type)`

### 8.3 `file_tools.io`
- Safe filesystem operations
- Atomic writer with locking
- Hashing utilities for audit

### 8.4 `file_tools.edit`
- Text edits (sed-like)
- Structured editors for each format
- Produces diffs (or diff summaries) for audit and preview

### 8.5 `file_tools.validate`
- Validators per filetype
- Unified result format (errors, warnings, valid)

### 8.6 `file_tools.audit`
- Event builder + append-only JSONL writer
- Snapshot manager hooks

### 8.7 `file_tools.convert`
- Backend registry for converters
- Capability detection and selection

### 8.8 `file_mcp_server`
- Transport (stdio/socket/http depending on your chosen MCP runtime)
- Auth (API key check)
- Tool discovery and dispatch
- Error normalisation

### 8.9 FastMCP integration notes
FastMCP is the reference MCP runtime targeted for HTTP/SSE compliance.

- **Server creation**: `mcp = FastMCP("Name")`, then register tools via `@mcp.tool`.
- **Run**: `mcp.run()` defaults to **stdio**; use `mcp.run(transport="http", host=..., port=...)`
  for **Streamable HTTP** transport. HTTP defaults to an MCP endpoint at `/mcp/`.
- **HTTP ASGI app**: `mcp.http_app(path="/api/mcp/")` returns an ASGI app for mounting.
- **FastAPI integration**: mount MCP in FastAPI and **pass the MCP lifespan** to FastAPI:
  `api = FastAPI(lifespan=mcp_app.lifespan)` then `api.mount("/mcp", mcp_app)`.
  Lifespan wiring is required for FastMCP session management to initialize correctly.
- **Custom routes** (health checks): use `@mcp.custom_route("/health", methods=["GET"])`.
- **Authentication**: FastMCP supports bearer/JWT/OAuth auth helpers. For simple auth,
  `BearerTokenAuth(token=...)` can be passed into `FastMCP(...)`.
- **HTTP scalability**: Streamable HTTP is stateful by default. Enable stateless mode
  for horizontal scaling: `FastMCP(..., stateless_http=True)` or
  `mcp.run(transport="http", stateless_http=True)`.
- **Legacy SSE**: `transport="sse"` is supported for backwards compatibility, but
  Streamable HTTP is the recommended transport for new deployments.

---

## 9. Execution Flows

### 9.1 Read flow
1. Authenticate request
2. Load active profile config
3. ScopePolicy allows `read`
4. Read file (safe decode)
5. Return content + metadata

### 9.2 Structured edit flow (mutation)
1. Authenticate request
2. Load config + apply scope/type constraints
3. (Optional) pre-validate original
4. Apply edit in-memory (or temp copy)
5. Generate preview diff (for response + audit)
6. Snapshot original (if enabled)
7. Atomic write + fsync
8. Post-validate (per policy)
9. Write audit event (success/failure with details)
10. Return result + warnings

---

## 10. Error Handling Contract

All tools return:
- `ok: bool`
- `result: ...` (tool-specific)
- `warnings: []`
- `errors: []` (structured)
- `meta: {timings, profile, validation}`

Strict mode failures must:
- not modify the target file
- still emit an audit record for the attempt

---

## 11. Extensibility

### 11.1 Tool plugins
Tools are registered through a registry module. Adding a new tool requires:
- Input/output models
- Handler function
- Capability flags
- Unit tests

### 11.2 Converter backends
Conversion backends follow a common interface:
- `can_handle(input_type, target_type) -> bool`
- `is_available() -> bool` (checks external binaries)
- `convert(...) -> ConversionResult`

---

## 12. Testing Strategy

- Unit tests for:
  - ScopePolicy traversal prevention
  - Atomic write correctness
  - Editors per format
  - Validators per format
- Integration tests for:
  - Full edit transaction with snapshots + audit
  - Conversion pipeline with and without external tools
- Golden tests for diffs and markdown section edits

---

## 13. POSIX Operational Recommendations

- Run under a dedicated user with constrained permissions
- Mount or chroot/jail if available (deployment-specific)
- Keep snapshot and audit directories on the same filesystem for consistency (or explicitly support cross-device moves)
- Rotate operational logs; keep audit logs append-only with retention rules

---

## 14. Out of Scope (explicit)
- Any LLM integration
- Network crawling or internet search (only local filesystem search)
- UI frontend (beyond optional `meld` invocation)
