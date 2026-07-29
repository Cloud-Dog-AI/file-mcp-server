# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Google Drive admin OAuth flow helpers for server-hosted setup pages.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Handles OAuth start/callback, folder validation, and DB-backed profile updates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from threading import Lock
import secrets
from typing import Dict, MutableMapping
from urllib.parse import parse_qs, urlencode, urlparse

from file_tools.adapters import get as http_get
from file_tools.adapters import post as http_post


MASKED_CLIENT_SECRET = "********"


@dataclass
class PendingGoogleDriveAuth:
    created_at: float
    profile: str
    user_email: str
    folder_input: str
    client_id: str
    client_secret: str
    oauth_scope: str
    oauth_authorize_uri: str
    api_base_uri: str
    redirect_uri: str
    token_uri: str


@dataclass
class GoogleDriveBindResult:
    profile: str
    user_email: str
    folder_id: str
    folder_name: str
    folder_url: str
    config_path: str
    db_row_id: str | None = None  # W28C-1702 (FM8): id of the durable file_storage_profiles row


_PENDING: Dict[str, PendingGoogleDriveAuth] = {}
_PENDING_LOCK = Lock()


def _clean(value: str | None) -> str:
    """Handle clean."""
    return (value or "").strip()


def _normalise_base_uri(value: str) -> str:
    """Return a cleaned base URI without a trailing slash."""
    return _clean(value).rstrip("/")


def _looks_like_url(value: str) -> bool:
    """Return whether the supplied value can be treated as a URL."""
    parsed = urlparse(value)
    return bool(parsed.scheme and parsed.netloc)


def _drive_api_url(base_uri: str, path: str) -> str:
    """Build a Google Drive API URL from configured base URI and a relative path."""
    return f"{_normalise_base_uri(base_uri)}/{path.lstrip('/')}"


def _extract_folder_id(folder_input: str) -> tuple[str | None, str | None]:
    """Handle extract folder id."""
    value = _clean(folder_input)
    if not value:
        return None, None
    if _looks_like_url(value):
        parsed = urlparse(value)
        parts = [p for p in parsed.path.split("/") if p]
        if "folders" in parts:
            idx = parts.index("folders")
            if idx + 1 < len(parts):
                return parts[idx + 1], value
        query = parse_qs(parsed.query)
        if query.get("id"):
            return query["id"][0], value
        return None, value
    return value, None


def _build_auth_url(
    client_id: str,
    redirect_uri: str,
    state: str,
    *,
    oauth_scope: str,
    oauth_authorize_uri: str,
) -> str:
    """Handle build auth url."""
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": oauth_scope,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{_normalise_base_uri(oauth_authorize_uri)}?{urlencode(params)}"


def parse_form_urlencoded(body: bytes) -> dict[str, str]:
    """Parse form urlencoded."""
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {k: (v[0] if v else "") for k, v in parsed.items()}


# Shared admin-page styling (platform-consistent: clean card on the Cloud-Dog
# gradient, system font stack, accessible focus/contrast). Used by the setup and
# link-success pages so the server-rendered admin flow matches the platform UI.
_ADMIN_PAGE_CSS = """
  :root{--bg1:#0b1220;--bg2:#1e293b;--card:#ffffff;--fg:#1f2933;--muted:#5b6675;
        --border:#e3e8ef;--accent:#2563eb;--accent-d:#1d4ed8;--ok:#15803d;--ok-bg:#ecfdf3;--ok-bd:#abefc6;}
  *{box-sizing:border-box}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
       margin:0;min-height:100vh;color:var(--fg);background:linear-gradient(135deg,var(--bg1),var(--bg2));
       display:flex;align-items:center;justify-content:center;padding:24px;line-height:1.5;}
  .card{background:var(--card);width:100%;max-width:600px;border-radius:16px;
        box-shadow:0 24px 60px rgba(2,6,23,.45);overflow:hidden;}
  .card__body{padding:36px 40px 40px;}
  .brand{font-size:.78rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);font-weight:700;}
  .badge{width:64px;height:64px;border-radius:50%;background:var(--ok-bg);border:1px solid var(--ok-bd);
         display:flex;align-items:center;justify-content:center;margin:18px 0 8px;}
  .badge svg{width:32px;height:32px;color:var(--ok);}
  h1{font-size:1.5rem;margin:.3rem 0 .4rem;}
  .muted{color:var(--muted);}
  dl{display:grid;grid-template-columns:auto 1fr;gap:8px 16px;margin:22px 0 10px;
     padding:16px 18px;background:#f8fafc;border:1px solid var(--border);border-radius:12px;font-size:.95rem;}
  dt{color:var(--muted);font-weight:600;} dd{margin:0;font-weight:600;word-break:break-word;}
  .note{display:flex;gap:10px;align-items:flex-start;margin-top:16px;padding:12px 14px;border-radius:10px;
        background:var(--ok-bg);border:1px solid var(--ok-bd);color:#14532d;font-size:.9rem;}
  .note svg{flex:none;margin-top:1px;color:var(--ok);}
  .actions{display:flex;gap:12px;margin-top:26px;flex-wrap:wrap;}
  .btn{appearance:none;border:0;cursor:pointer;text-decoration:none;font-weight:600;font-size:.95rem;
       padding:11px 18px;border-radius:10px;display:inline-flex;align-items:center;gap:8px;}
  .btn--primary{background:var(--accent);color:#fff;} .btn--primary:hover{background:var(--accent-d);}
  .btn--ghost{background:#fff;color:var(--fg);border:1px solid var(--border);} .btn--ghost:hover{background:#f1f5f9;}
  a.link{color:var(--accent);text-decoration:none;font-weight:600;} a.link:hover{text-decoration:underline;}
  a:focus-visible,button:focus-visible{outline:3px solid #93c5fd;outline-offset:2px;}
"""


def render_link_success_page(
    result: "GoogleDriveBindResult",
    *,
    continue_url: str = "/admin/google-drive",
    persisted: bool = True,
) -> str:
    """Render the styled, platform-consistent Google Drive link-success page.

    Operator/client-facing: shows the linked folder + a durable-storage assurance
    and clear continue links. It NEVER exposes internal paths (config.yaml) or DB
    row ids — those remain server-side audit detail only (logged, not rendered)."""
    profile = escape(result.profile or "google_drive")
    folder = escape(result.folder_name or "Google Drive folder")
    folder_url = (result.folder_url or "").strip()
    safe_url = escape(folder_url)
    open_btn = (
        f'<a class="btn btn--ghost" href="{safe_url}" target="_blank" rel="noopener">Open in Drive</a>'
        if folder_url
        else ""
    )
    folder_link = (
        f'<p style="margin:.2rem 0 0"><a class="link" href="{safe_url}" target="_blank" '
        f'rel="noopener">Open folder in Google Drive &#8599;</a></p>'
        if folder_url
        else ""
    )
    note = (
        "Saved securely. Your Google Drive connection is stored in the server database "
        "and will persist across restarts and container recreates."
        if persisted
        else "Connection applied for this session, but it was NOT saved durably. "
        "Please contact an administrator."
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Google Drive linked</title>
  <style>{_ADMIN_PAGE_CSS}</style>
</head>
<body>
  <main class="card" role="main">
    <div class="card__body">
      <div class="brand">Cloud-Dog &middot; File MCP</div>
      <div class="badge" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
             stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
      </div>
      <h1>Google Drive linked successfully</h1>
      <p class="muted">Your Google Drive folder is now connected to the <b>{profile}</b> profile.</p>
      <dl>
        <dt>Profile</dt><dd>{profile}</dd>
        <dt>Folder</dt><dd>{folder}</dd>
      </dl>
      {folder_link}
      <div class="note" role="status">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor"
             stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11"
             width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
        <span>{escape(note)}</span>
      </div>
      <div class="actions">
        <a class="btn btn--primary" href="{escape(continue_url)}">Continue</a>
        {open_btn}
      </div>
    </div>
  </main>
</body>
</html>"""


def render_setup_page(
    *,
    callback_url: str,
    profiles: list[str],
    selected_profile: str | None = None,
    lock_profile: bool = False,
    status_message: str = "",
    status_type: str = "info",
    prefills: dict[str, str] | None = None,
    has_client_secret: bool = False,
    folder_url_example: str = "",
    status_banner: str = "",
) -> str:
    """Execute render setup page.

    W28C-1702 (FM9): ``status_banner`` is server-rendered HTML reflecting the
    profile's DB-row state (NOT CONFIGURED / PARTIALLY CONFIGURED / CONFIGURED).
    It is the authoritative connection indicator — the form's localStorage no
    longer remembers credentials/identity (which faked an "already connected"
    state with no real server-side badge).
    """
    prefills = prefills or {}

    def _prefill(name: str) -> str:
        """Handle prefill."""
        return escape(_clean(prefills.get(name)))

    resolved_profile = (
        selected_profile
        if selected_profile in profiles
        else (profiles[0] if profiles else "")
    )
    options = "".join(
        f'<option value="{escape(name)}"{" selected" if name == resolved_profile else ""}>{escape(name)}</option>'
        for name in profiles
    )
    if lock_profile:
        profile_input = (
            f"<input type='hidden' name='profile' value='{escape(resolved_profile)}' />"
            f"<input value='{escape(resolved_profile)}' disabled />"
            "<div class='hint'>Profile is fixed for this authorisation flow.</div>"
        )
    else:
        profile_input = f"<select name='profile'>{options}</select>"
    status_html = ""
    if status_message:
        color = (
            "#0b5"
            if status_type == "ok"
            else "#b50"
            if status_type == "warn"
            else "#444"
        )
        status_html = f'<p style="padding:8px;border:1px solid {color};color:{color};">{escape(status_message)}</p>'
    default_redirect = _prefill("redirect_uri") or escape(callback_url)
    default_token_uri = _prefill("token_uri")
    default_oauth_scope = _prefill("oauth_scope")
    default_oauth_authorise_uri = _prefill("oauth_authorize_uri")
    default_api_base_uri = _prefill("api_base_uri")
    resolved_folder_url_example = _clean(folder_url_example) or _prefill(
        "folder_url_example"
    )
    folder_url_example_value = escape(
        resolved_folder_url_example or "drive.google.com/drive/folders/..."
    )
    user_email_value = _prefill("user_email")
    folder_input_value = _prefill("folder_input")
    client_id_value = _prefill("client_id")
    client_secret_value = (
        MASKED_CLIENT_SECRET if has_client_secret else _prefill("client_secret")
    )
    client_secret_hint = (
        "Stored secret is masked. Leave as-is to reuse it, or replace with a new secret."
        if has_client_secret
        else "Paste OAuth client secret."
    )
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Google Drive Setup</title>
  <style>
    body {{ font-family: sans-serif; margin: 24px; max-width: 840px; }}
    label {{ display:block; margin-top: 12px; font-weight: 600; }}
    input, select {{ width: 100%; padding: 8px; }}
    .hint {{ font-size: 0.9em; color: #666; }}
    button {{ margin-top: 16px; padding: 10px 14px; }}
    code {{ background: #f4f4f4; padding: 2px 4px; }}
  </style>
</head>
<body>
  <h1>Google Drive Profile Setup</h1>
  {status_banner}
  {status_html}
  <p>Configure Google Drive for a selected file-mcp-server profile.</p>
  <form method="post" action="/admin/google-drive/start">
    <label>Profile</label>
    {profile_input}
    <label>Google account email</label>
    <input name="user_email" placeholder="name@example.com" value="{user_email_value}" />
    <label>Folder input</label>
    <input name="folder_input" placeholder="Folder ID, share URL, or folder name" value="{folder_input_value}" />
    <div class="hint">Example URL: <code>{folder_url_example_value}</code></div>
    <label>OAuth client id</label>
    <input name="client_id" value="{client_id_value}" />
    <label>OAuth client secret</label>
    <input name="client_secret" type="password" value="{escape(client_secret_value)}" />
    <div class="hint">{escape(client_secret_hint)}</div>
    <label>Redirect URI</label>
    <input name="redirect_uri" value="{default_redirect}" />
    <label>Token URI</label>
    <input name="token_uri" value="{default_token_uri}" />
    <input type="hidden" name="oauth_scope" value="{default_oauth_scope}" />
    <input type="hidden" name="oauth_authorize_uri" value="{default_oauth_authorise_uri}" />
    <input type="hidden" name="api_base_uri" value="{default_api_base_uri}" />
    <button type="submit">Start Google Authorisation</button>
  </form>
  <script>
    (function () {{
      var storageKey = "file_mcp_google_drive_setup_v1";
      // W28C-1702 (FM9): only operator-default fields are remembered locally —
      // NEVER credentials/identity (user_email/folder/client_id), which faked an
      // "already connected" state. The authoritative connection state is the
      // server-rendered banner above the form.
      var fields = ["redirect_uri", "token_uri"];
      var defaults = {{
        redirect_uri: "{default_redirect}",
        token_uri: "{default_token_uri}"
      }};

      function readStored() {{
        try {{
          var raw = window.localStorage.getItem(storageKey);
          if (!raw) return {{}};
          var parsed = JSON.parse(raw);
          return parsed && typeof parsed === "object" ? parsed : {{}};
        }} catch (_) {{
          return {{}};
        }}
      }}

      function writeStored(next) {{
        try {{
          window.localStorage.setItem(storageKey, JSON.stringify(next));
        }} catch (_) {{
          // ignore storage errors
        }}
      }}

      var form = document.querySelector("form[action='/admin/google-drive/start']");
      if (!form) return;
      var stored = readStored();
      fields.forEach(function (name) {{
        var el = form.elements.namedItem(name);
        if (!el) return;
        if ((!el.value || el.value.trim() === "") && typeof stored[name] === "string" && stored[name].length > 0) {{
          el.value = stored[name];
        }}
        if ((name === "redirect_uri" || name === "token_uri") && (!el.value || el.value.trim() === "")) {{
          el.value = defaults[name] || "";
        }}
        el.addEventListener("input", function () {{
          if ((name === "redirect_uri" || name === "token_uri") && (!el.value || el.value.trim() === "")) {{
            el.value = defaults[name] || "";
          }}
          stored[name] = el.value || "";
          writeStored(stored);
        }});
        el.addEventListener("change", function () {{
          if ((name === "redirect_uri" || name === "token_uri") && (!el.value || el.value.trim() === "")) {{
            el.value = defaults[name] || "";
          }}
          stored[name] = el.value || "";
          writeStored(stored);
        }});
      }});
    }})();
  </script>
</body>
</html>
"""


def begin_oauth(
    data: dict[str, str],
    *,
    pending_store: MutableMapping[str, PendingGoogleDriveAuth] | None = None,
) -> str:
    """Execute begin oauth."""
    profile = _clean(data.get("profile"))
    folder_input = _clean(data.get("folder_input"))
    client_id = _clean(data.get("client_id"))
    client_secret = _clean(data.get("client_secret"))
    oauth_scope = _clean(data.get("oauth_scope"))
    oauth_authorize_uri = _clean(data.get("oauth_authorize_uri"))
    api_base_uri = _clean(data.get("api_base_uri"))
    redirect_uri = _clean(data.get("redirect_uri"))
    token_uri = _clean(data.get("token_uri"))
    if not profile:
        raise ValueError("profile is required")
    if not folder_input:
        raise ValueError("folder_input is required")
    if not client_id:
        raise ValueError("client_id is required")
    if not client_secret:
        raise ValueError("client_secret is required")
    if not redirect_uri:
        raise ValueError("redirect_uri is required")
    if not token_uri:
        raise ValueError("token_uri is required")
    if not oauth_scope:
        raise ValueError("oauth_scope is required")
    if not oauth_authorize_uri:
        raise ValueError("oauth_authorize_uri is required")
    if not api_base_uri:
        raise ValueError("api_base_uri is required")

    state = secrets.token_urlsafe(24)
    pending = PendingGoogleDriveAuth(
        created_at=datetime.now(timezone.utc).timestamp(),
        profile=profile,
        user_email=_clean(data.get("user_email")),
        folder_input=folder_input,
        client_id=client_id,
        client_secret=client_secret,
        oauth_scope=oauth_scope,
        oauth_authorize_uri=oauth_authorize_uri,
        api_base_uri=api_base_uri,
        redirect_uri=redirect_uri,
        token_uri=token_uri,
    )
    with _PENDING_LOCK:
        # The HTTP runtime supplies its own store so the issued CSRF principal
        # and its pending OAuth data have one lifetime.  The module-global
        # store remains the compatibility default for direct helper callers.
        (pending_store if pending_store is not None else _PENDING)[state] = pending
    return _build_auth_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=state,
        oauth_scope=oauth_scope,
        oauth_authorize_uri=oauth_authorize_uri,
    )


def _take_pending(
    state: str,
    *,
    pending_store: MutableMapping[str, PendingGoogleDriveAuth] | None = None,
) -> PendingGoogleDriveAuth:
    """Handle take pending."""
    with _PENDING_LOCK:
        pending = (pending_store if pending_store is not None else _PENDING).pop(
            state, None
        )
    if pending is None:
        raise RuntimeError("Invalid or expired OAuth state")
    return pending


def _exchange_code(pending: PendingGoogleDriveAuth, code: str) -> tuple[str, str]:
    """Handle exchange code."""
    payload = {
        "client_id": pending.client_id,
        "client_secret": pending.client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": pending.redirect_uri,
    }
    response = http_post(pending.token_uri, data=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    access = _clean(data.get("access_token"))
    refresh = _clean(data.get("refresh_token"))
    if not access:
        raise RuntimeError("Token response missing access_token")
    return access, refresh


def _auth_headers(token: str) -> dict[str, str]:
    """Handle auth headers."""
    return {"Authorization": f"Bearer {token}"}


def _fetch_folder(
    access_token: str, folder_input: str, *, api_base_uri: str
) -> tuple[str, str, str]:
    """Handle fetch folder."""
    folder_id_guess, folder_url = _extract_folder_id(folder_input)
    if folder_id_guess:
        response = http_get(
            _drive_api_url(api_base_uri, f"/files/{folder_id_guess}"),
            headers=_auth_headers(access_token),
            params={"fields": "id,name,mimeType,webViewLink"},
            timeout=30,
        )
        if response.status_code != 404:
            response.raise_for_status()
            data = response.json()
            if data.get("mimeType") != "application/vnd.google-apps.folder":
                raise RuntimeError("Resolved id is not a Google Drive folder")
            return (
                data["id"],
                data.get("name", ""),
                folder_url or data.get("webViewLink", ""),
            )

    escaped = folder_input.replace("'", "\\'")
    q = f"name = '{escaped}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    params: dict[str, str | int] = {
        "q": q,
        "fields": "files(id,name,webViewLink,mimeType)",
        "pageSize": 5,
    }
    response = http_get(
        _drive_api_url(api_base_uri, "/files"),
        headers=_auth_headers(access_token),
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    files = response.json().get("files", [])
    if not files:
        raise RuntimeError("No Google Drive folder matched the provided folder name")
    first = files[0]
    return first["id"], first.get("name", ""), first.get("webViewLink", "")


def _merge_google_drive_into_profile(
    profile_mapping: Dict,
    *,
    user_email: str,
    folder_id: str,
    folder_url: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    access_token: str,
    redirect_uri: str,
    token_uri: str,
) -> Dict:
    """In-place: set the google_drive storage block on a profile mapping.

    W28C-1702 (FM8): used by the durable DB-row persister so Google Drive
    profile material is stored outside immutable runtime YAML config files.
    """
    storage = profile_mapping.setdefault("storage", {})
    if not isinstance(storage, dict):
        raise RuntimeError("profile.storage is not a mapping")
    storage["backend"] = "google_drive"
    drive = storage.setdefault("google_drive", {})
    if not isinstance(drive, dict):
        raise RuntimeError("profile.storage.google_drive is not a mapping")
    drive["user_email"] = user_email
    drive["folder_id"] = folder_id
    drive["folder_url"] = folder_url
    drive["client_id"] = client_id
    drive["client_secret"] = client_secret
    drive["refresh_token"] = refresh_token
    drive["access_token"] = access_token
    drive["redirect_uri"] = redirect_uri
    drive["token_uri"] = token_uri
    return profile_mapping

def _persist_profile_google_drive_to_db(
    *,
    db_session_manager,
    file_storage_profile_model,
    profile: str,
    user_email: str,
    folder_id: str,
    folder_url: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    access_token: str,
    redirect_uri: str,
    token_uri: str,
) -> str:
    """W28C-1702 (FM8): upsert OAuth tokens into file_storage_profiles.config_json.

    This is the DURABLE persistence path. ``/workspace/database/file_mcp.db``
    survives container recreates via the bind-mounted volume; the DB-overlay
    path in ``server_runtime._merge_active_db_profiles_into_config`` reads
    ``is_active=True`` rows back at startup and merges them into the runtime
    ProfileConfig with DB taking precedence over env-derived defaults.

    Behaviour:
      * Locate an is_active row matching ``profile`` (preferred); else any
        active row whose backend is ``google_drive``; else create a NEW row.
      * Merge captured GDrive fields into the row's existing config_json
        (preserving auth, scope, etc.).
      * Soft-deleted ``<name>__deleted_<ts>_<rand>`` rows stay archived (audit).

    Returns the DB row id for evidence/audit-log citation.
    """
    import json as _json
    import uuid as _uuid

    with db_session_manager.session() as session:
        row = (
            session.query(file_storage_profile_model)
            .filter_by(name=profile, is_active=True)
            .first()
        )
        existing_config: Dict = {}
        if row is not None:
            try:
                existing_config = _json.loads(row.config_json) if row.config_json else {}
            except Exception:
                existing_config = {}
        else:
            row = (
                session.query(file_storage_profile_model)
                .filter_by(backend="google_drive", is_active=True)
                .first()
            )
            if row is not None:
                try:
                    existing_config = (
                        _json.loads(row.config_json) if row.config_json else {}
                    )
                except Exception:
                    existing_config = {}

        if not isinstance(existing_config, dict):
            existing_config = {}

        merged = _merge_google_drive_into_profile(
            dict(existing_config),
            user_email=user_email,
            folder_id=folder_id,
            folder_url=folder_url,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            access_token=access_token,
            redirect_uri=redirect_uri,
            token_uri=token_uri,
        )
        merged_json = _json.dumps(merged, sort_keys=False)

        if row is None:
            row_id = f"prof_{_uuid.uuid4().hex[:12]}"
            row = file_storage_profile_model(
                id=row_id,
                name=profile,
                display_name=profile,
                backend="google_drive",
                config_json=merged_json,
                is_active=True,
            )
            session.add(row)
        else:
            row.backend = "google_drive"
            row.config_json = merged_json
            row.is_active = True
            row_id = row.id

        session.commit()
        return str(row_id)


def complete_oauth_callback(
    *,
    state: str,
    code: str,
    config_path: Path,
    db_session_manager=None,
    file_storage_profile_model=None,
    reload_callback=None,
    pending_store: MutableMapping[str, PendingGoogleDriveAuth] | None = None,
) -> GoogleDriveBindResult:
    """Execute complete oauth callback.

    W28C-1702 (FM8): callers SHOULD supply ``db_session_manager`` +
    ``file_storage_profile_model`` + ``reload_callback`` so captured OAuth
    tokens persist to the DB (the ONLY durable home — ``/app/config.yaml`` is
    ephemeral and lost on container recreate, and OAuth secrets are never written
    there). W28M-1605-FIX: the durable DB store is now MANDATORY — the callback
    refuses to complete without ``db_session_manager`` + ``file_storage_profile_model``
    rather than silently leaving the credentials non-durable.
    """
    # W28M-1605-FIX: fail fast — the DB is the SOLE durable credential store.
    # config.yaml never holds the secrets, so without the DB the tokens would not
    # persist at all. Refuse BEFORE consuming the one-time OAuth code.
    if db_session_manager is None or file_storage_profile_model is None:
        raise RuntimeError(
            "Google Drive OAuth completion requires a durable database store "
            "(db_session_manager + file_storage_profile_model). Refusing to complete: "
            "OAuth secrets are never written to config.yaml, so without the DB the "
            "captured credentials would be lost on container recreate."
        )
    pending = _take_pending(state, pending_store=pending_store)
    access_token, refresh_token = _exchange_code(pending, code)
    folder_id, folder_name, folder_url = _fetch_folder(
        access_token, pending.folder_input, api_base_uri=pending.api_base_uri
    )
    # DURABLE persistence: DB row (the only path that survives container
    # recreate — RULES §0A.WS bind-mounted /workspace volume + W28M-1603 brief).
    # config.yaml/default.yaml/defaults.yaml are immutable runtime inputs and are
    # not updated by the OAuth callback.
    # Guaranteed present by the guard above.
    db_row_id = None
    if db_session_manager is not None and file_storage_profile_model is not None:
        db_row_id = _persist_profile_google_drive_to_db(
            db_session_manager=db_session_manager,
            file_storage_profile_model=file_storage_profile_model,
            profile=pending.profile,
            user_email=pending.user_email,
            folder_id=folder_id,
            folder_url=folder_url,
            client_id=pending.client_id,
            client_secret=pending.client_secret,
            refresh_token=refresh_token,
            access_token=access_token,
            redirect_uri=pending.redirect_uri,
            token_uri=pending.token_uri,
        )
        # Live refresh: re-merge DB profiles into runtime config without
        # waiting for a container recreate.
        if callable(reload_callback):
            try:
                reload_callback()
            except Exception:  # noqa: BLE001
                # Refresh failure is non-fatal — the row is durable; the next
                # restart picks it up via _merge_active_db_profiles_into_config.
                pass
    return GoogleDriveBindResult(
        profile=pending.profile,
        user_email=pending.user_email,
        folder_id=folder_id,
        folder_name=folder_name,
        folder_url=folder_url,
        config_path=str(config_path),
        db_row_id=db_row_id,
    )
