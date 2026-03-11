#!/usr/bin/env python3
"""Google Drive OAuth helper.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Generate OAuth URL and exchange authorization code for refresh token.
"""

from __future__ import annotations

import argparse
import os
from urllib.parse import urlencode

import requests


DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/drive",
]
DEFAULT_REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _require(value: str | None, name: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise SystemExit(f"Missing required value: {name}")
    return cleaned


def build_auth_url(
    client_id: str, redirect_uri: str, scopes: list[str], state: str | None = None
) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
    }
    if state:
        params["state"] = state
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def exchange_code(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    token_uri: str,
) -> dict:
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    response = requests.post(token_uri, data=data, timeout=30)
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Google Drive OAuth helper for file-mcp-server",
        epilog=(
            "Get client_id/client_secret from Google Cloud Console: "
            "APIs & Services -> Credentials -> Create Credentials -> OAuth client ID (Desktop app)."
        ),
    )
    parser.add_argument(
        "--client-id", default=os.getenv("FILE_MCP_GDRIVE_CLIENT_ID", "")
    )
    parser.add_argument(
        "--client-secret", default=os.getenv("FILE_MCP_GDRIVE_CLIENT_SECRET", "")
    )
    parser.add_argument(
        "--redirect-uri",
        default=os.getenv("FILE_MCP_GDRIVE_REDIRECT_URI", DEFAULT_REDIRECT_URI),
    )
    parser.add_argument(
        "--token-uri", default=os.getenv("FILE_MCP_GDRIVE_TOKEN_URI", DEFAULT_TOKEN_URI)
    )
    parser.add_argument("--scopes", default=",".join(DEFAULT_SCOPES))
    parser.add_argument("--state", default="")
    parser.add_argument("--code", default="")
    args = parser.parse_args()

    client_id = _require(args.client_id, "FILE_MCP_GDRIVE_CLIENT_ID")
    redirect_uri = args.redirect_uri or DEFAULT_REDIRECT_URI
    scopes = [scope.strip() for scope in args.scopes.split(",") if scope.strip()]
    auth_url = build_auth_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scopes=scopes,
        state=args.state or None,
    )

    print("Authorization URL:")
    print(auth_url)
    print("")
    if not args.code:
        print(
            "Paste the returned authorization code and rerun with --code <value> to exchange tokens."
        )
        return

    client_secret = _require(args.client_secret, "FILE_MCP_GDRIVE_CLIENT_SECRET")
    payload = exchange_code(
        client_id=client_id,
        client_secret=client_secret,
        code=args.code,
        redirect_uri=redirect_uri,
        token_uri=(args.token_uri or DEFAULT_TOKEN_URI),
    )
    print("Token exchange response received.")
    print("Set these env values:")
    print(f"FILE_MCP_GDRIVE_CLIENT_ID={client_id}")
    print(f"FILE_MCP_GDRIVE_CLIENT_SECRET={client_secret}")
    print(f"FILE_MCP_GDRIVE_REDIRECT_URI={redirect_uri}")
    print(f"FILE_MCP_GDRIVE_TOKEN_URI={args.token_uri or DEFAULT_TOKEN_URI}")
    print(f"FILE_MCP_GDRIVE_ACCESS_TOKEN={payload.get('access_token', '')}")
    print(f"FILE_MCP_GDRIVE_REFRESH_TOKEN={payload.get('refresh_token', '')}")


if __name__ == "__main__":
    main()
