---
template-id: T-WUI
template-version: 1.0
applies-to: docs/WEBUI-REFERENCE.md
registry: service
required: conditional
when-applicable: ""
template-last-updated: 2026-06-12
template-owner: platform-standards

project: file-mcp-server
doc-last-updated: 2026-06-24
doc-git-commit: 24cd1ac046fd3b0da63e4dcfc9cbdc0188ca6947
doc-git-branch: main
doc-source-shas: []
doc-age-policy: 90d
doc-conformance-stamp: 2026-06-24T00:00:00Z
---

# file-mcp-server — WEBUI-REFERENCE

> **Template version:** T-WUI v1.0 — conditional: service has a WebUI panel.

Source files verified: `src/file_mcp_server/server_runtime.py` (`_ui_route_paths`), `src/file_mcp_server/web_flat_roles.py`, `cloud-dog-ai-ui-monorepo/apps/file-mcp/src/routes/App.tsx`, `cloud-dog-ai-ui-monorepo/apps/file-mcp/src/lib/rbac.ts`.

## 1. Panel structure

The SPA is served from `ui/dist/index.html`. The backend mounts it at the `/ui` base path (configurable via `FILE_MCP_HTTP_BASE_PATH`, default `/ui`) and serves only registered client-side routes. Legacy WebUI aliases return HTTP `308` redirects to the canonical routes below.

| Route | Panel | Roles | Backend route |
|---|---|---|---|
| `/` | Dashboard | all authenticated | `GET /` (status) |
| `/login` | Login page (redirects to `/` when authenticated) | unauthenticated | `POST /auth/login` |
| `/file-browser` | File Browser — browse, read, write, delete files | all authenticated | `POST /mcp` (`read_file`, `write_file`, `list_dir`, …) |
| `/search` | Search — search paths and content | all authenticated | `POST /mcp` (`search_paths`, `search_content`) |
| `/storage-profiles` | Storage Profiles — manage named storage backends | admin only | `GET/POST/PUT/DELETE /admin/profiles` |
| `/audit-log` | Audit Log — read audit event stream | admin / read-write | `GET /api/v1/jobs` + audit log file |
| `/system/jobs` | Jobs — view managed background jobs | all authenticated | `GET /api/v1/jobs`, `GET /api/v1/jobs/{id}` |
| `/developer/api-docs` | API Docs — embedded OpenAPI explorer | all authenticated | `GET /openapi.json` |
| `/developer/mcp-console` | MCP Console — interactive MCP JSON-RPC testing | all authenticated | `POST /webmcp` |
| `/developer/a2a-console` | A2A Console — agent task submission | all authenticated | `POST /a2a/tasks` |
| `/google-drive-settings` | Google Drive Settings — OAuth / credential config | admin only (requires `admin:google_drive` permission) | `GET/POST /admin/google-drive` |
| `/admin/users` | Identity — Users | admin only | `GET/POST /admin/users` |
| `/admin/groups` | Identity — Groups | admin only | `GET/POST /admin/groups` |
| `/admin/api-keys` | Identity — API Keys | admin only | `GET/POST /admin/api-keys` |
| `/admin/roles` | Identity — Roles | admin only | (read-only display) |
| `/admin/rbac` | Identity — RBAC | admin only | (read-only display) |
| `/system/settings` | Settings — session and UI preferences | all authenticated | client-side only |
| `/system/about` | About — service version and info | all authenticated | `GET /health` |

Legacy aliases (all `308` redirect): `/ui/login` -> `/login`, `/dashboard` -> `/`, `/idam/users` -> `/admin/users`, `/idam/groups` -> `/admin/groups`, `/idam/api-keys` -> `/admin/api-keys`, `/idam/roles` -> `/admin/roles`, `/idam/rbac` -> `/admin/rbac`, `/admin-identity` -> `/admin/users`, `/admin/identity` -> `/admin/users`, `/api-docs` -> `/developer/api-docs`, `/mcp-console` -> `/developer/mcp-console`, `/a2a-console` -> `/developer/a2a-console`, `/jobs` -> `/system/jobs`, `/settings` -> `/system/settings`, and `/about` -> `/system/about`. Query strings are preserved.

## 2. Login

- **Auth mode:** Cookie-based (`file_web_session`; `HttpOnly; SameSite=Lax; Max-Age=3600; Path=/`). Configured via `FILE_MCP_UI_AUTH_MODE` (default: `cookie`; also accepts `api_key` or `oidc`).
- **Flow:** POST credentials to `POST /auth/login` with JSON body `{"username": "...", "password": "..."}`. On success, server sets `file_web_session` cookie and returns a JSON payload including `role` and optionally `access_token`.
- **Roles (flat):** Three roles resolved via `web_flat_roles.py` from `cloud_dog_idam` RBAC catalog:
  - `admin` — full access including identity management and storage profiles
  - `read-write` — file operations (read + write) and job monitoring; no identity/profile admin
  - `read-only` — file read and search only; all mutating MCP tools blocked
- **Session timeout:** Configurable via `SESSION_TIMEOUT_MINUTES` runtime config (SPA inactivity timer). Default: no timeout.
- **Logout:** `POST /auth/logout` clears the session cookie.
- **`/auth/me`:** `GET /auth/me` returns current session user/role info; returns `401` when not authenticated.

## 3. RBAC visibility matrix

| Panel | admin | read-write | read-only |
|---|---|---|---|
| Dashboard | visible | visible | visible |
| File Browser | read + write + delete | read + write + delete | read only |
| Search | visible | visible | visible |
| Storage Profiles | full CRUD | hidden | hidden |
| Audit Log | visible | visible | hidden |
| Jobs | visible | visible | visible |
| API Docs | visible | visible | visible |
| MCP Console | visible | visible | visible |
| A2A Console | visible | visible | visible |
| Google Drive Settings | visible (if `admin:google_drive`) | hidden | hidden |
| Identity (Users/Groups/API Keys/Roles/RBAC) | full CRUD | hidden | hidden |
| Settings | visible | visible | visible |
| About | visible | visible | visible |

Affordance gating is enforced both client-side (nav items hidden) and server-side (write MCP tools + admin endpoints return `403` for insufficient role).

## 4. Static routes

Registered in `server_runtime.py` `_ui_route_paths()`:

```
/
/login
/dashboard
/file-browser
/search
/storage-profiles
/audit-log
/developer/api-docs
/developer/mcp-console
/developer/a2a-console
/system/jobs
/system/settings
/system/about
/admin/users
/admin/groups
/admin/api-keys
/admin/roles
/admin/rbac
/google-drive-settings
```

Unknown root-level paths do not fall back to the SPA entry point. This keeps API/admin typos visible as `404` and prevents accidental UI masking of unregistered routes.

## 5. Cross-references
- [API-REFERENCE.md](API-REFERENCE.md)
- [ROLES-AND-USECASES.md](ROLES-AND-USECASES.md)
- PS-77-webui-comprehensive.md
- PS-30-ui.md

## 6. Project-specific notes

- The SPA is compiled from `cloud-dog-ai-ui-monorepo/apps/file-mcp` and vendored into `ui/dist/`.
- Runtime configuration is injected at `/runtime-config.js` (served by the backend) which sets `window.__RUNTIME_CONFIG__` — this includes `AUTH_MODE`, `MCP_BASE_URL`, `DEFAULT_BROWSE_PATH`, etc.
- The WebUI MCP path is `/webmcp` (distinct from the API `/mcp` path) to allow cookie-auth MCP calls from the browser.
- Google Drive Settings visibility is gated on the `canManageGoogleDriveSettings` permission check (`admin:google_drive` or admin wildcard `*`).
