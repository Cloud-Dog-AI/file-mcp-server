#!/usr/bin/env python3
"""Interactive Google Drive configuration setup for file-mcp-server.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Prompts for Google account/folder, performs OAuth, validates access, and writes env settings.
"""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from dataclasses import dataclass
from pathlib import Path
import secrets
import sys
import threading
import time
from typing import Iterable
from urllib.parse import parse_qs, urlparse

import requests

# Allow direct execution (`python scripts/google_drive_setup.py`) without
# requiring package installation.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from google_drive_oauth_helper import (
    DEFAULT_REDIRECT_URI,
    DEFAULT_SCOPES,
    DEFAULT_TOKEN_URI,
    build_auth_url,
    exchange_code,
)


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _ask(prompt: str, *, default: str = "", required: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        raw = input(f"{prompt}{suffix}: ").strip()
        value = raw or default
        if not required or value:
            return value
        print("Value is required.")


def _is_local_redirect_uri(redirect_uri: str) -> bool:
    parsed = urlparse(redirect_uri)
    return parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}


def _wait_for_local_oauth_code(redirect_uri: str, timeout_s: int) -> str | None:
    parsed = urlparse(redirect_uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or 80
    expected_path = parsed.path or "/"
    code_holder: dict[str, str] = {}

    class _CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            request_path = urlparse(self.path).path or "/"
            if request_path != expected_path:
                self.send_response(404)
                self.end_headers()
                return
            query = parse_qs(urlparse(self.path).query)
            code = (query.get("code") or [""])[0]
            if code:
                code_holder["code"] = code
                body = (
                    "Google authorization received. You can close this tab and return to the terminal."
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                body = "Missing authorization code in callback URL.".encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    server = HTTPServer((host, port), _CallbackHandler)
    server.timeout = 0.5

    def _serve() -> None:
        deadline = time.time() + timeout_s
        while time.time() < deadline and "code" not in code_holder:
            server.handle_request()

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    thread.join(timeout=timeout_s + 1)
    server.server_close()
    return code_holder.get("code")


def extract_folder_id(folder_input: str) -> tuple[str | None, str | None]:
    """Return (folder_id, folder_url_if_url)."""
    text = _clean(folder_input)
    if not text:
        return None, None
    if text.startswith("http://") or text.startswith("https://"):
        parsed = urlparse(text)
        parts = [part for part in parsed.path.split("/") if part]
        if "folders" in parts:
            idx = parts.index("folders")
            if idx + 1 < len(parts):
                return parts[idx + 1], text
        query = parse_qs(parsed.query)
        if query.get("id"):
            return query["id"][0], text
        return None, text
    # Treat as literal id or name; caller determines fallback.
    return text, None


def _read_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def write_env_values(path: Path, values: dict[str, str]) -> None:
    """Update/append KEY=VALUE pairs preserving other keys and comments."""
    existing_lines: list[str] = []
    key_to_index: dict[str, int] = {}
    if path.exists():
        existing_lines = path.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(existing_lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, _ = stripped.split("=", 1)
            key_to_index[key.strip()] = idx

    for key, value in values.items():
        rendered = f"{key}={value}"
        if key in key_to_index:
            existing_lines[key_to_index[key]] = rendered
        else:
            existing_lines.append(rendered)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(existing_lines).rstrip() + "\n", encoding="utf-8")


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@dataclass(frozen=True)
class FolderInfo:
    folder_id: str
    name: str
    web_view_link: str


def _verify_token(access_token: str, timeout_s: int) -> dict:
    response = requests.get(
        "https://www.googleapis.com/drive/v3/about",
        headers=_auth_headers(access_token),
        params={"fields": "user(displayName,emailAddress)"},
        timeout=timeout_s,
    )
    response.raise_for_status()
    payload = response.json()
    user = payload.get("user", {})
    return {"display_name": user.get("displayName", ""), "email": user.get("emailAddress", "")}


def _folder_info(access_token: str, folder_id: str, timeout_s: int) -> FolderInfo:
    response = requests.get(
        f"https://www.googleapis.com/drive/v3/files/{folder_id}",
        headers=_auth_headers(access_token),
        params={"fields": "id,name,mimeType,webViewLink"},
        timeout=timeout_s,
    )
    response.raise_for_status()
    payload = response.json()
    mime = payload.get("mimeType")
    if mime != "application/vnd.google-apps.folder":
        raise RuntimeError(f"Resolved id is not a folder: {folder_id} (mimeType={mime})")
    return FolderInfo(
        folder_id=payload.get("id", folder_id),
        name=payload.get("name", ""),
        web_view_link=payload.get("webViewLink", ""),
    )


def _find_folders_by_name(access_token: str, folder_name: str, timeout_s: int) -> list[FolderInfo]:
    escaped = folder_name.replace("'", "\\'")
    q = f"name = '{escaped}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    response = requests.get(
        "https://www.googleapis.com/drive/v3/files",
        headers=_auth_headers(access_token),
        params={"q": q, "fields": "files(id,name,webViewLink,mimeType)", "pageSize": 20},
        timeout=timeout_s,
    )
    response.raise_for_status()
    files = response.json().get("files", [])
    out: list[FolderInfo] = []
    for item in files:
        if item.get("mimeType") == "application/vnd.google-apps.folder":
            out.append(
                FolderInfo(
                    folder_id=item.get("id", ""),
                    name=item.get("name", ""),
                    web_view_link=item.get("webViewLink", ""),
                )
            )
    return [f for f in out if f.folder_id]


def _choose_folder(candidates: Iterable[FolderInfo]) -> FolderInfo:
    options = list(candidates)
    if not options:
        raise RuntimeError("No folder candidates available")
    if len(options) == 1:
        return options[0]
    print("\nMultiple folders matched. Choose one:")
    for idx, info in enumerate(options, start=1):
        print(f"{idx}. {info.name} ({info.folder_id}) {info.web_view_link}")
    while True:
        raw = input("Selection number: ").strip()
        try:
            sel = int(raw)
        except ValueError:
            sel = 0
        if 1 <= sel <= len(options):
            return options[sel - 1]
        print("Invalid selection.")


def configure_google_drive(args: argparse.Namespace) -> int:
    env_path = Path(_clean(args.env_path) or "private/env-google-drive")
    env_values = _read_env(env_path)

    print("Google Drive configuration setup")
    print("--------------------------------")
    account_email = _ask("Google account email", default=_clean(args.email) or env_values.get("FILE_MCP_GDRIVE_USER_EMAIL", ""))
    folder_input = _ask(
        "Folder input (folder id, folder share URL, or folder name)",
        default=_clean(args.folder) or env_values.get("FILE_MCP_GDRIVE_FOLDER_ID", "") or env_values.get("FILE_MCP_GDRIVE_FOLDER_URL", ""),
        required=True,
    )
    client_id = _ask("OAuth client id", default=_clean(args.client_id) or env_values.get("FILE_MCP_GDRIVE_CLIENT_ID", ""), required=True)
    redirect_uri = _ask(
        "Redirect URI",
        default=_clean(args.redirect_uri) or env_values.get("FILE_MCP_GDRIVE_REDIRECT_URI", DEFAULT_REDIRECT_URI),
        required=True,
    )
    token_uri = _ask(
        "Token URI",
        default=_clean(args.token_uri) or env_values.get("FILE_MCP_GDRIVE_TOKEN_URI", DEFAULT_TOKEN_URI),
        required=True,
    )

    scopes = [scope.strip() for scope in (_clean(args.scopes) or ",".join(DEFAULT_SCOPES)).split(",") if scope.strip()]
    state = secrets.token_urlsafe(12)
    challenge_url = build_auth_url(client_id=client_id, redirect_uri=redirect_uri, scopes=scopes, state=state)
    print("\nOpen this URL in your browser and authorize access:\n")
    print(challenge_url)
    print("")

    client_secret = _ask(
        "OAuth client secret",
        default=_clean(args.client_secret) or env_values.get("FILE_MCP_GDRIVE_CLIENT_SECRET", ""),
        required=True,
    )
    code = _clean(args.code)
    if not code and _is_local_redirect_uri(redirect_uri):
        if _clean(args.auto_capture_code).lower() in {"1", "true", "yes", "on"}:
            print(f"Waiting for callback on {redirect_uri} (timeout {args.callback_timeout_s}s)...")
            code = _wait_for_local_oauth_code(redirect_uri, timeout_s=int(args.callback_timeout_s)) or ""
            if code:
                print("Authorization code captured from callback.")
            else:
                print("No callback captured before timeout; please paste code manually.")
    if not code:
        code = _ask("Paste authorization code", default=_clean(args.code), required=True)

    payload = exchange_code(
        client_id=client_id,
        client_secret=client_secret,
        code=code,
        redirect_uri=redirect_uri,
        token_uri=token_uri,
    )
    access_token = _clean(payload.get("access_token"))
    refresh_token = _clean(payload.get("refresh_token")) or env_values.get("FILE_MCP_GDRIVE_REFRESH_TOKEN", "")
    if not access_token:
        raise RuntimeError("Token exchange succeeded but access_token was missing.")
    if not refresh_token:
        print("Warning: refresh_token was not returned. Existing env refresh token will be retained if present.")

    user_info = _verify_token(access_token, timeout_s=int(args.timeout_s))
    folder_id_guess, folder_url = extract_folder_id(folder_input)
    selected_folder: FolderInfo
    if folder_id_guess and folder_id_guess == folder_input.strip() and not folder_input.startswith("http"):
        # Could be folder id or name. Try id first.
        try:
            selected_folder = _folder_info(access_token, folder_id_guess, timeout_s=int(args.timeout_s))
        except Exception:
            matches = _find_folders_by_name(access_token, folder_input.strip(), timeout_s=int(args.timeout_s))
            if not matches:
                raise RuntimeError(f"Unable to resolve folder id or name: {folder_input}") from None
            selected_folder = _choose_folder(matches)
    elif folder_id_guess:
        selected_folder = _folder_info(access_token, folder_id_guess, timeout_s=int(args.timeout_s))
    else:
        matches = _find_folders_by_name(access_token, folder_input.strip(), timeout_s=int(args.timeout_s))
        if not matches:
            raise RuntimeError(f"Unable to resolve folder: {folder_input}")
        selected_folder = _choose_folder(matches)

    print("\nValidation successful:")
    print(f"- Authenticated user: {user_info.get('display_name', '')} <{user_info.get('email', '')}>")
    print(f"- Folder: {selected_folder.name} ({selected_folder.folder_id})")
    print(f"- Folder URL: {selected_folder.web_view_link}")

    target_path = _ask("Env file path to save", default=str(env_path), required=True)
    env_out = Path(target_path)
    write_env_values(
        env_out,
        {
            "FILE_MCP_STORAGE_BACKEND": "google_drive",
            "FILE_MCP_GDRIVE_USER_EMAIL": account_email or user_info.get("email", ""),
            "FILE_MCP_GDRIVE_FOLDER_ID": selected_folder.folder_id,
            "FILE_MCP_GDRIVE_FOLDER_URL": folder_url or selected_folder.web_view_link,
            "FILE_MCP_GDRIVE_CLIENT_ID": client_id,
            "FILE_MCP_GDRIVE_CLIENT_SECRET": client_secret,
            "FILE_MCP_GDRIVE_REFRESH_TOKEN": refresh_token,
            "FILE_MCP_GDRIVE_ACCESS_TOKEN": access_token,
            "FILE_MCP_GDRIVE_REDIRECT_URI": redirect_uri,
            "FILE_MCP_GDRIVE_TOKEN_URI": token_uri,
        },
    )
    print(f"\nSaved Google Drive configuration to: {env_out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Interactive Google Drive env setup for file-mcp-server",
        epilog=(
            "Need a client_id/client_secret? Use Google Cloud Console -> APIs & Services -> "
            "Credentials -> Create Credentials -> OAuth client ID."
        ),
    )
    parser.add_argument("--email", default="")
    parser.add_argument("--folder", default="")
    parser.add_argument("--env-path", default="private/env-google-drive")
    parser.add_argument("--client-id", default="")
    parser.add_argument("--client-secret", default="")
    parser.add_argument("--redirect-uri", default=DEFAULT_REDIRECT_URI)
    parser.add_argument("--token-uri", default=DEFAULT_TOKEN_URI)
    parser.add_argument("--scopes", default=",".join(DEFAULT_SCOPES))
    parser.add_argument("--code", default="")
    parser.add_argument("--timeout-s", default="30")
    parser.add_argument("--auto-capture-code", default="true")
    parser.add_argument("--callback-timeout-s", default="180")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(configure_google_drive(args))


if __name__ == "__main__":
    main()
