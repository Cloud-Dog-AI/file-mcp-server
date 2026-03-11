"""Google Drive admin OAuth flow helpers for server-hosted setup pages.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Handles OAuth start/callback, folder validation, and profile config updates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from threading import Lock
import secrets
from typing import Dict
from urllib.parse import parse_qs, urlencode, urlparse

from cloud_dog_config.yaml_loader import load_yaml  # type: ignore[import-untyped]
from file_tools.adapters import get as http_get
from file_tools.adapters import post as http_post
from file_tools.adapters import safe_dump


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
) -> str:
    """Execute render setup page."""
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
      var fields = ["profile", "user_email", "folder_input", "client_id", "redirect_uri", "token_uri"];
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


def begin_oauth(data: dict[str, str]) -> str:
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
        _PENDING[state] = pending
    return _build_auth_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=state,
        oauth_scope=oauth_scope,
        oauth_authorize_uri=oauth_authorize_uri,
    )


def _take_pending(state: str) -> PendingGoogleDriveAuth:
    """Handle take pending."""
    with _PENDING_LOCK:
        pending = _PENDING.pop(state, None)
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


def _update_profile_google_drive(
    *,
    config_path: Path,
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
) -> None:
    """Handle update profile google drive."""
    raw = load_yaml(str(config_path), missing_ok=True)
    raw.setdefault("profiles", {})
    profiles = raw["profiles"]
    if not isinstance(profiles, dict):
        raise RuntimeError("profiles is not a mapping")
    profiles.setdefault(profile, {})
    prof = profiles[profile]
    if not isinstance(prof, dict):
        raise RuntimeError(f"profile {profile} is not a mapping")
    storage = prof.setdefault("storage", {})
    if not isinstance(storage, dict):
        raise RuntimeError(f"profile {profile}.storage is not a mapping")
    storage["backend"] = "google_drive"
    drive = storage.setdefault("google_drive", {})
    if not isinstance(drive, dict):
        raise RuntimeError(f"profile {profile}.storage.google_drive is not a mapping")
    drive["user_email"] = user_email
    drive["folder_id"] = folder_id
    drive["folder_url"] = folder_url
    drive["client_id"] = client_id
    drive["client_secret"] = client_secret
    drive["refresh_token"] = refresh_token
    drive["access_token"] = access_token
    drive["redirect_uri"] = redirect_uri
    drive["token_uri"] = token_uri
    config_path.write_text(safe_dump(raw, sort_keys=False), encoding="utf-8")


def complete_oauth_callback(
    *, state: str, code: str, config_path: Path
) -> GoogleDriveBindResult:
    """Execute complete oauth callback."""
    pending = _take_pending(state)
    access_token, refresh_token = _exchange_code(pending, code)
    folder_id, folder_name, folder_url = _fetch_folder(
        access_token, pending.folder_input, api_base_uri=pending.api_base_uri
    )
    _update_profile_google_drive(
        config_path=config_path,
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
    return GoogleDriveBindResult(
        profile=pending.profile,
        user_email=pending.user_email,
        folder_id=folder_id,
        folder_name=folder_name,
        folder_url=folder_url,
        config_path=str(config_path),
    )
