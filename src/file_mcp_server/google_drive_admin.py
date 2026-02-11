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

import requests
import yaml


DEFAULT_SCOPE = "https://www.googleapis.com/auth/drive"
DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"


@dataclass
class PendingGoogleDriveAuth:
    created_at: float
    profile: str
    user_email: str
    folder_input: str
    client_id: str
    client_secret: str
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
    return (value or "").strip()


def _extract_folder_id(folder_input: str) -> tuple[str | None, str | None]:
    value = _clean(folder_input)
    if not value:
        return None, None
    if value.startswith("http://") or value.startswith("https://"):
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


def _build_auth_url(client_id: str, redirect_uri: str, state: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": DEFAULT_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def parse_form_urlencoded(body: bytes) -> dict[str, str]:
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {k: (v[0] if v else "") for k, v in parsed.items()}


def render_setup_page(
    *,
    callback_url: str,
    profiles: list[str],
    status_message: str = "",
    status_type: str = "info",
) -> str:
    options = "".join(f'<option value="{escape(name)}">{escape(name)}</option>' for name in profiles)
    status_html = ""
    if status_message:
        color = "#0b5" if status_type == "ok" else "#b50" if status_type == "warn" else "#444"
        status_html = f'<p style="padding:8px;border:1px solid {color};color:{color};">{escape(status_message)}</p>'
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
    <select name="profile">{options}</select>
    <label>Google account email</label>
    <input name="user_email" placeholder="name@example.com" />
    <label>Folder input</label>
    <input name="folder_input" placeholder="Folder ID, share URL, or folder name" />
    <div class="hint">Example URL: <code>https://drive.google.com/drive/folders/...</code></div>
    <label>OAuth client id</label>
    <input name="client_id" />
    <label>OAuth client secret</label>
    <input name="client_secret" type="password" />
    <label>Redirect URI</label>
    <input name="redirect_uri" value="{escape(callback_url)}" />
    <label>Token URI</label>
    <input name="token_uri" value="{escape(DEFAULT_TOKEN_URI)}" />
    <button type="submit">Start Google Authorization</button>
  </form>
</body>
</html>
"""


def begin_oauth(data: dict[str, str]) -> str:
    profile = _clean(data.get("profile"))
    folder_input = _clean(data.get("folder_input"))
    client_id = _clean(data.get("client_id"))
    client_secret = _clean(data.get("client_secret"))
    redirect_uri = _clean(data.get("redirect_uri"))
    token_uri = _clean(data.get("token_uri")) or DEFAULT_TOKEN_URI
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

    state = secrets.token_urlsafe(24)
    pending = PendingGoogleDriveAuth(
        created_at=datetime.now(timezone.utc).timestamp(),
        profile=profile,
        user_email=_clean(data.get("user_email")),
        folder_input=folder_input,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        token_uri=token_uri,
    )
    with _PENDING_LOCK:
        _PENDING[state] = pending
    return _build_auth_url(client_id=client_id, redirect_uri=redirect_uri, state=state)


def _take_pending(state: str) -> PendingGoogleDriveAuth:
    with _PENDING_LOCK:
        pending = _PENDING.pop(state, None)
    if pending is None:
        raise RuntimeError("Invalid or expired OAuth state")
    return pending


def _exchange_code(pending: PendingGoogleDriveAuth, code: str) -> tuple[str, str]:
    payload = {
        "client_id": pending.client_id,
        "client_secret": pending.client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": pending.redirect_uri,
    }
    response = requests.post(pending.token_uri, data=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    access = _clean(data.get("access_token"))
    refresh = _clean(data.get("refresh_token"))
    if not access:
        raise RuntimeError("Token response missing access_token")
    return access, refresh


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _fetch_folder(access_token: str, folder_input: str) -> tuple[str, str, str]:
    folder_id_guess, folder_url = _extract_folder_id(folder_input)
    if folder_id_guess:
        response = requests.get(
            f"https://www.googleapis.com/drive/v3/files/{folder_id_guess}",
            headers=_auth_headers(access_token),
            params={"fields": "id,name,mimeType,webViewLink"},
            timeout=30,
        )
        if response.status_code != 404:
            response.raise_for_status()
            data = response.json()
            if data.get("mimeType") != "application/vnd.google-apps.folder":
                raise RuntimeError("Resolved id is not a Google Drive folder")
            return data["id"], data.get("name", ""), folder_url or data.get("webViewLink", "")

    escaped = folder_input.replace("'", "\\'")
    q = f"name = '{escaped}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    response = requests.get(
        "https://www.googleapis.com/drive/v3/files",
        headers=_auth_headers(access_token),
        params={"q": q, "fields": "files(id,name,webViewLink,mimeType)", "pageSize": 5},
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
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise RuntimeError(f"Invalid YAML object in {config_path}")
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
    config_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")


def complete_oauth_callback(*, state: str, code: str, config_path: Path) -> GoogleDriveBindResult:
    pending = _take_pending(state)
    access_token, refresh_token = _exchange_code(pending, code)
    folder_id, folder_name, folder_url = _fetch_folder(access_token, pending.folder_input)
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
