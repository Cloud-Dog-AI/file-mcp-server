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

"""Google Drive storage backend using Drive v3 REST API.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: OAuth refresh-token based Google Drive backend for file operations.
"""

from __future__ import annotations

import json
import mimetypes
import posixpath
import time
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse

from file_tools.adapters import HTTPError, Response
from file_tools.adapters import request as http_request

from file_tools.config.models import StorageConfig

from .base import (
    NotSupportedError,
    StorageBackend,
    StorageEntry,
    StorageStat,
    ensure_no_unresolved_placeholder,
)


FOLDER_MIME = "application/vnd.google-apps.folder"
DEFAULT_UPLOAD_BASE_URI = "https://www.googleapis.com/upload/drive/v3"


def _clean_posix(path: str) -> str:
    """Handle clean posix."""
    if not path:
        return "/"
    if not path.startswith("/"):
        path = "/" + path
    norm = posixpath.normpath(path)
    if not norm.startswith("/"):
        norm = "/" + norm
    return norm


def _to_bool(value: object) -> bool:
    """Handle to bool."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized or "${" in normalized:
            return False
        return normalized in {"1", "true", "yes", "on"}
    return False


def _extract_folder_id(folder_id: str | None, folder_url: str | None) -> str | None:
    """Handle extract folder id."""
    if folder_id and folder_id.strip():
        return folder_id.strip()
    if not folder_url:
        return None
    parsed = urlparse(folder_url)
    # Expected forms:
    # - /drive/folders/<id>
    # - open?id=<id>
    parts = [part for part in parsed.path.split("/") if part]
    if "folders" in parts:
        idx = parts.index("folders")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    query = parse_qs(parsed.query)
    if query.get("id"):
        return query["id"][0]
    return None


def _normalise_base_uri(value: str | None) -> str:
    """Return a base URI without a trailing slash."""
    return (value or "").strip().rstrip("/")


class GoogleDriveStorage(StorageBackend):
    backend_name = "google_drive"

    def __init__(self, storage: StorageConfig, *, timeout_s: int | None = None) -> None:
        """Initialise the instance state."""
        cfg = storage.google_drive
        ensure_no_unresolved_placeholder(
            cfg.folder_id, field_name="google_drive.folder_id"
        )
        ensure_no_unresolved_placeholder(
            cfg.folder_url, field_name="google_drive.folder_url"
        )
        ensure_no_unresolved_placeholder(
            cfg.client_id, field_name="google_drive.client_id"
        )
        ensure_no_unresolved_placeholder(
            cfg.client_secret, field_name="google_drive.client_secret"
        )
        ensure_no_unresolved_placeholder(
            cfg.refresh_token, field_name="google_drive.refresh_token"
        )
        ensure_no_unresolved_placeholder(
            cfg.access_token, field_name="google_drive.access_token"
        )
        ensure_no_unresolved_placeholder(
            cfg.token_uri, field_name="google_drive.token_uri"
        )
        ensure_no_unresolved_placeholder(
            cfg.api_base_uri, field_name="google_drive.api_base_uri"
        )
        ensure_no_unresolved_placeholder(
            cfg.upload_base_uri, field_name="google_drive.upload_base_uri"
        )
        folder_id = _extract_folder_id(cfg.folder_id, cfg.folder_url)
        if not folder_id:
            raise ValueError(
                "Google Drive storage requires google_drive.folder_id or google_drive.folder_url"
            )
        if not cfg.client_id or not cfg.client_secret:
            raise ValueError(
                "Google Drive storage requires google_drive.client_id and google_drive.client_secret"
            )
        if not (cfg.refresh_token or cfg.access_token):
            raise ValueError(
                "Google Drive storage requires google_drive.refresh_token or google_drive.access_token"
            )

        self._folder_id = folder_id
        self._client_id = cfg.client_id
        self._client_secret = cfg.client_secret
        self._refresh_token = cfg.refresh_token
        self._access_token = cfg.access_token
        if not cfg.token_uri:
            raise ValueError("Google Drive storage requires google_drive.token_uri")
        if not cfg.api_base_uri:
            raise ValueError("Google Drive storage requires google_drive.api_base_uri")
        self._token_uri = cfg.token_uri.strip()
        self._api_base_uri = _normalise_base_uri(cfg.api_base_uri)
        self._upload_base_uri = _normalise_base_uri(
            cfg.upload_base_uri or DEFAULT_UPLOAD_BASE_URI
        )
        self._timeout_s = int(timeout_s) if timeout_s is not None else 30
        self._token_expires_at: float | None = None

        insecure = _to_bool(storage.tls.insecure_skip_verify)
        self._verify: bool | str = True
        if insecure:
            self._verify = False
        elif storage.tls.ca_bundle_path:
            self._verify = storage.tls.ca_bundle_path

    def _api_url(self, path: str) -> str:
        """Build a Drive API URL from configured base URI and relative path."""
        return f"{self._api_base_uri}/{path.lstrip('/')}"

    def _upload_url(self, path: str) -> str:
        """Build a Drive upload URL from configured base URI and relative path."""
        return f"{self._upload_base_uri}/{path.lstrip('/')}"

    def _token(self) -> str:
        """Handle token."""
        now = time.time()
        if (
            self._access_token
            and self._token_expires_at
            and now < self._token_expires_at - 30
        ):
            return self._access_token
        if self._access_token and not self._refresh_token:
            return self._access_token
        if not self._refresh_token:
            raise RuntimeError("Google Drive OAuth refresh token not configured")
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": self._refresh_token,
            "grant_type": "refresh_token",
        }
        resp = http_request(
            "POST",
            self._token_uri,
            data=data,
            timeout=self._timeout_s,
            verify=self._verify,
        )
        try:
            resp.raise_for_status()
        except HTTPError as exc:
            try:
                payload = resp.json()
            except Exception:
                payload = {}
            if isinstance(payload, dict):
                error = str(payload.get("error") or "").strip()
                description = str(payload.get("error_description") or "").strip()
                if error or description:
                    detail = ": ".join(part for part in (error, description) if part)
                    raise RuntimeError(
                        f"Google Drive token refresh failed: {detail}"
                    ) from exc
            raise
        payload = resp.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError(
                "Google Drive token refresh response missing access_token"
            )
        self._access_token = token
        expires_in = payload.get("expires_in")
        if isinstance(expires_in, int):
            self._token_expires_at = time.time() + expires_in
        return token

    def _headers(self) -> dict[str, str]:
        """Handle headers."""
        return {"Authorization": f"Bearer {self._token()}"}

    def _request(self, method: str, url: str, **kwargs) -> Response:
        """Handle request."""
        headers = dict(kwargs.pop("headers", {}) or {})
        headers.update(self._headers())
        params = dict(kwargs.pop("params", {}) or {})
        if url.startswith(f"{self._api_base_uri}/"):
            params.setdefault("supportsAllDrives", True)
            if url.rstrip("/").endswith("/files"):
                params.setdefault("includeItemsFromAllDrives", True)
        return http_request(
            method,
            url,
            headers=headers,
            params=params,
            timeout=self._timeout_s,
            verify=self._verify,
            **kwargs,
        )

    def _lookup_child(self, parent_id: str, name: str) -> dict[str, Any] | None:
        """Handle lookup child."""
        escaped_name = name.replace("'", "\\'")
        q = f"'{parent_id}' in parents and name = '{escaped_name}' and trashed = false"
        resp = self._request(
            "GET",
            self._api_url("/files"),
            params={"q": q, "fields": "files(id,name,mimeType,size)"},
        )
        resp.raise_for_status()
        files = resp.json().get("files", [])
        return files[0] if files else None

    def _resolve_path(
        self, path: str, *, create_dirs: bool = False
    ) -> tuple[str, bool]:
        """Handle resolve path."""
        logical = _clean_posix(path)
        if logical == "/":
            return self._folder_id, True
        current = self._folder_id
        parts = [p for p in logical.split("/") if p]
        for idx, part in enumerate(parts):
            child = self._lookup_child(current, part)
            is_last = idx == len(parts) - 1
            if child is None:
                if create_dirs or not is_last:
                    folder = self._create_folder(current, part)
                    current = folder["id"]
                    continue
                raise FileNotFoundError(path)
            current = child["id"]
        info = self._get_metadata(current)
        return current, info.get("mimeType") == FOLDER_MIME

    def _get_metadata(self, file_id: str) -> dict[str, Any]:
        """Handle get metadata."""
        resp = self._request(
            "GET",
            self._api_url(f"/files/{file_id}"),
            params={"fields": "id,name,mimeType,size,parents"},
        )
        if resp.status_code == 404:
            raise FileNotFoundError(file_id)
        resp.raise_for_status()
        return resp.json()

    def _create_folder(self, parent_id: str, name: str) -> dict[str, Any]:
        """Handle create folder."""
        payload = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}
        resp = self._request(
            "POST",
            self._api_url("/files"),
            json=payload,
            params={"fields": "id,name,mimeType,size"},
        )
        resp.raise_for_status()
        return resp.json()

    def read_bytes(self, path: str) -> bytes:
        """Read bytes."""
        file_id, is_dir = self._resolve_path(path)
        if is_dir:
            raise IsADirectoryError(path)
        resp = self._request(
            "GET",
            self._api_url(f"/files/{file_id}"),
            params={"alt": "media"},
            stream=True,
        )
        resp.raise_for_status()
        return resp.content

    def write_bytes(self, path: str, data: bytes, *, overwrite: bool = True) -> None:
        """Write bytes."""
        logical = _clean_posix(path)
        parent_path = _clean_posix(posixpath.dirname(logical))
        name = posixpath.basename(logical)
        if not name:
            raise ValueError("File name is required")
        parent_id, _ = self._resolve_path(parent_path, create_dirs=True)
        existing = self._lookup_child(parent_id, name)
        mime_type = mimetypes.guess_type(name)[0] or "application/octet-stream"

        if existing and not overwrite:
            raise FileExistsError(path)

        metadata = {"name": name, "parents": [parent_id]}
        if existing:
            # Updating an existing file should not force parent rewrites; some
            # shared/linked folders allow content updates but reject parent changes.
            patch_meta = {"name": name}
            files = {
                "metadata": ("metadata", json.dumps(patch_meta), "application/json"),
                "file": (name, data, mime_type),
            }
            url = self._upload_url(f"/files/{existing['id']}")
            resp = self._request(
                "PATCH", url, params={"uploadType": "multipart"}, files=files
            )
        else:
            files = {
                "metadata": ("metadata", json.dumps(metadata), "application/json"),
                "file": (name, data, mime_type),
            }
            url = self._upload_url("/files")
            resp = self._request(
                "POST", url, params={"uploadType": "multipart"}, files=files
            )
        resp.raise_for_status()

    def delete_path(self, path: str, *, missing_ok: bool = False) -> None:
        """Delete path."""
        try:
            file_id, _ = self._resolve_path(path)
        except FileNotFoundError:
            if missing_ok:
                return
            raise
        resp = self._request("DELETE", self._api_url(f"/files/{file_id}"))
        if resp.status_code == 404 and missing_ok:
            return
        resp.raise_for_status()

    def stat(self, path: str) -> StorageStat | None:
        """Execute stat."""
        try:
            file_id, is_dir = self._resolve_path(path)
        except FileNotFoundError:
            return None
        meta = self._get_metadata(file_id)
        size = None
        if not is_dir and meta.get("size") is not None:
            try:
                size = int(meta["size"])
            except (TypeError, ValueError):
                size = None
        return StorageStat(path=_clean_posix(path), is_dir=is_dir, size=size)

    def list_dir(self, path: str, *, recursive: bool = False) -> list[StorageEntry]:
        """List dir."""
        root_path = _clean_posix(path)
        root_id, is_dir = self._resolve_path(root_path)
        if not is_dir:
            raise NotADirectoryError(path)

        entries: list[StorageEntry] = []
        queue: list[tuple[str, str]] = [(root_id, root_path)]
        while queue:
            parent_id, logical_parent = queue.pop(0)
            q = f"'{parent_id}' in parents and trashed = false"
            resp = self._request(
                "GET",
                self._api_url("/files"),
                params={"q": q, "fields": "files(id,name,mimeType,size)"},
            )
            resp.raise_for_status()
            files = resp.json().get("files", [])
            for item in files:
                child_path = _clean_posix(
                    posixpath.join(logical_parent, item.get("name", ""))
                )
                child_is_dir = item.get("mimeType") == FOLDER_MIME
                entries.append(StorageEntry(path=child_path, is_dir=child_is_dir))
                if recursive and child_is_dir:
                    queue.append((item["id"], child_path))
        return entries

    def iter_paths(
        self, roots: Iterable[str], *, max_depth: int | None = None
    ) -> Iterable[str]:
        """Execute iter paths."""
        for root in roots:
            base = _clean_posix(root)
            queue: list[tuple[str, int]] = [(base, 0)]
            while queue:
                current, depth = queue.pop(0)
                try:
                    entries = self.list_dir(current, recursive=False)
                except FileNotFoundError:
                    continue
                for entry in entries:
                    next_depth = depth + 1
                    if entry.is_dir:
                        if max_depth is None or next_depth <= max_depth:
                            queue.append((entry.path, next_depth))
                        continue
                    if max_depth is None or next_depth <= max_depth:
                        yield entry.path

    def create_dir(
        self, path: str, *, parents: bool = True, exist_ok: bool = True
    ) -> None:
        """Create dir."""
        logical = _clean_posix(path)
        if logical == "/":
            return
        parts = [p for p in logical.split("/") if p]
        current = self._folder_id
        for part in parts:
            child = self._lookup_child(current, part)
            if child is None:
                child = self._create_folder(current, part)
            elif child.get("mimeType") != FOLDER_MIME:
                raise NotADirectoryError(path)
            current = child["id"]

    def copy_path(self, src: str, dst: str, *, overwrite: bool = False) -> None:
        """Copy path."""
        src_id, src_is_dir = self._resolve_path(src)
        if src_is_dir:
            raise NotSupportedError("copy_path_directory", backend=self.backend_name)
        dst_logical = _clean_posix(dst)
        parent_path = _clean_posix(posixpath.dirname(dst_logical))
        name = posixpath.basename(dst_logical)
        parent_id, _ = self._resolve_path(parent_path, create_dirs=True)
        existing = self._lookup_child(parent_id, name)
        if existing and not overwrite:
            raise FileExistsError(dst)
        if existing and overwrite:
            self._request(
                "DELETE", self._api_url(f"/files/{existing['id']}")
            ).raise_for_status()
        payload = {"name": name, "parents": [parent_id]}
        resp = self._request(
            "POST",
            self._api_url(f"/files/{src_id}/copy"),
            json=payload,
        )
        resp.raise_for_status()

    def move_path(self, src: str, dst: str, *, overwrite: bool = False) -> None:
        """Move path."""
        src_id, _ = self._resolve_path(src)
        dst_logical = _clean_posix(dst)
        parent_path = _clean_posix(posixpath.dirname(dst_logical))
        name = posixpath.basename(dst_logical)
        parent_id, _ = self._resolve_path(parent_path, create_dirs=True)
        existing = self._lookup_child(parent_id, name)
        if existing and not overwrite:
            raise FileExistsError(dst)
        if existing and overwrite:
            self._request(
                "DELETE", self._api_url(f"/files/{existing['id']}")
            ).raise_for_status()
        meta = self._get_metadata(src_id)
        prev_parents = ",".join(meta.get("parents") or [])
        resp = self._request(
            "PATCH",
            self._api_url(f"/files/{src_id}"),
            params={"addParents": parent_id, "removeParents": prev_parents},
            json={"name": name},
        )
        resp.raise_for_status()

    def chmod_path(self, path: str, mode: int, *, recursive: bool = False) -> None:
        """Execute chmod path."""
        raise NotSupportedError("chmod_path", backend=self.backend_name)
