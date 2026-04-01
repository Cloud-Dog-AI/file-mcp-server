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

"""
file-mcp-server — file_tools/storage/s3.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for storage s3.py.
"""

from __future__ import annotations

import hashlib
import hmac
import posixpath
from datetime import datetime, timezone
from urllib.parse import quote, urljoin, urlparse

from xml.etree import ElementTree as ET

from file_tools.adapters import Response
from file_tools.adapters import request as http_request
from file_tools.config.models import StorageConfig

from .base import (
    NotSupportedError,
    StorageBackend,
    StorageEntry,
    StorageStat,
    ensure_no_unresolved_placeholder,
)


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


def _sha256_hex(data: bytes) -> str:
    """Handle sha256 hex."""
    return hashlib.sha256(data).hexdigest()


def _hmac(key: bytes, msg: str) -> bytes:
    """Handle hmac."""
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _aws_v4_signing_key(
    secret_key: str, date_yyyymmdd: str, region: str, service: str
) -> bytes:
    """Handle aws v4 signing key."""
    k_date = _hmac(("AWS4" + secret_key).encode("utf-8"), date_yyyymmdd)
    k_region = _hmac(k_date, region)
    k_service = _hmac(k_region, service)
    k_signing = _hmac(k_service, "aws4_request")
    return k_signing


def _canonical_query(params: dict[str, str]) -> str:
    # AWS expects sorted, URL-encoded parameters.
    """Handle canonical query."""
    items = sorted(
        (quote(k, safe="-_.~"), quote(v, safe="-_.~")) for k, v in params.items()
    )
    return "&".join(f"{k}={v}" for k, v in items)


def _canonical_headers(headers: dict[str, str]) -> tuple[str, str]:
    """Handle canonical headers."""
    normalized = {
        k.strip().lower(): " ".join(v.strip().split()) for k, v in headers.items()
    }
    keys = sorted(normalized.keys())
    canon = "".join(f"{k}:{normalized[k]}\n" for k in keys)
    signed = ";".join(keys)
    return canon, signed


class S3Storage(StorageBackend):
    backend_name = "s3"

    def __init__(self, storage: StorageConfig, *, timeout_s: int | None = None) -> None:
        """Initialise the instance state."""
        cfg = storage.s3
        ensure_no_unresolved_placeholder(cfg.endpoint, field_name="s3.endpoint")
        ensure_no_unresolved_placeholder(cfg.bucket, field_name="s3.bucket")
        ensure_no_unresolved_placeholder(cfg.access_key, field_name="s3.access_key")
        ensure_no_unresolved_placeholder(cfg.secret_key, field_name="s3.secret_key")
        if not cfg.endpoint:
            raise ValueError("S3 storage requires s3.endpoint")
        if not cfg.bucket:
            raise ValueError("S3 storage requires s3.bucket")
        if not cfg.access_key or not cfg.secret_key:
            raise ValueError("S3 storage requires s3.access_key and s3.secret_key")
        self._endpoint = cfg.endpoint.rstrip("/")
        self._bucket = cfg.bucket
        self._region = (cfg.region or "us-east-1").strip() or "us-east-1"
        self._access_key = cfg.access_key
        self._secret_key = cfg.secret_key
        self._prefix = _clean_posix(cfg.prefix or "/").lstrip("/")

        insecure = _to_bool(storage.tls.insecure_skip_verify)
        self._verify: bool | str = True
        if insecure:
            self._verify = False
        elif storage.tls.ca_bundle_path:
            self._verify = storage.tls.ca_bundle_path
        self._timeout_s = int(timeout_s) if timeout_s is not None else 30

    def _key(self, path: str) -> str:
        """Handle key."""
        rel = _clean_posix(path).lstrip("/")
        if self._prefix:
            if rel:
                return f"{self._prefix.rstrip('/')}/{rel}"
            return self._prefix.rstrip("/")
        return rel

    def _object_url(self, key: str) -> str:
        # Path-style: {endpoint}/{bucket}/{key}
        """Handle object url."""
        base = f"{self._endpoint.rstrip('/')}/"
        safe_key = "/".join(quote(seg) for seg in key.split("/")) if key else ""
        return urljoin(base, f"{quote(self._bucket)}/{safe_key}")

    def _sign_request(
        self,
        *,
        method: str,
        url: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        payload: bytes = b"",
    ) -> dict[str, str]:
        """Handle sign request."""
        parsed = urlparse(url)
        host = parsed.netloc
        canonical_uri = parsed.path or "/"
        canonical_uri = quote(canonical_uri, safe="/-_.~")
        canonical_query = _canonical_query(params or {})

        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        hdrs = {
            "host": host,
            "x-amz-date": amz_date,
            "x-amz-content-sha256": _sha256_hex(payload),
        }
        if headers:
            for k, v in headers.items():
                hdrs[k.lower()] = v

        canonical_headers, signed_headers = _canonical_headers(hdrs)
        canonical_request = (
            f"{method}\n"
            f"{canonical_uri}\n"
            f"{canonical_query}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{hdrs['x-amz-content-sha256']}"
        )
        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{self._region}/s3/aws4_request"
        string_to_sign = (
            f"{algorithm}\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )
        signing_key = _aws_v4_signing_key(
            self._secret_key, date_stamp, self._region, "s3"
        )
        signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        authorization = (
            f"{algorithm} "
            f"Credential={self._access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        out = {k: v for k, v in hdrs.items()}
        out["Authorization"] = authorization
        return out

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        data: bytes = b"",
    ) -> Response:
        """Handle request."""
        signed = self._sign_request(
            method=method, url=url, params=params, headers=headers, payload=data
        )
        return http_request(
            method,
            url,
            params=params,
            headers=signed,
            data=data,
            verify=self._verify,
            timeout=self._timeout_s,
        )

    def read_bytes(self, path: str) -> bytes:
        """Read bytes."""
        key = self._key(path)
        url = self._object_url(key)
        resp = self._request("GET", url)
        if resp.status_code == 404:
            raise FileNotFoundError(path)
        resp.raise_for_status()
        return resp.content

    def write_bytes(self, path: str, data: bytes, *, overwrite: bool = True) -> None:
        """Write bytes."""
        key = self._key(path)
        url = self._object_url(key)
        if not overwrite:
            # Use conditional put if supported: If-None-Match: *
            headers = {"If-None-Match": "*"}
        else:
            headers = {}
        resp = self._request("PUT", url, headers=headers, data=data)
        if resp.status_code == 412 and not overwrite:
            raise FileExistsError(path)
        resp.raise_for_status()

    def delete_path(self, path: str, *, missing_ok: bool = False) -> None:
        """Delete path."""
        key = self._key(path)
        url = self._object_url(key)
        resp = self._request("DELETE", url)
        if resp.status_code == 404 and missing_ok:
            return
        if resp.status_code == 404:
            raise FileNotFoundError(path)
        resp.raise_for_status()

    def stat(self, path: str) -> StorageStat | None:
        """Execute stat."""
        key = self._key(path)
        url = self._object_url(key)
        resp = self._request("HEAD", url)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        size = resp.headers.get("Content-Length")
        try:
            parsed = int(size) if size is not None else None
        except ValueError:
            parsed = None
        return StorageStat(path=_clean_posix(path), is_dir=False, size=parsed)

    def list_dir(self, path: str, *, recursive: bool = False) -> list[StorageEntry]:
        # S3 has no directories; emulate based on prefixes.
        """List dir."""
        prefix_key = self._key(path).rstrip("/")
        if prefix_key:
            prefix_key = prefix_key + "/"
        params: dict[str, str] = {"list-type": "2", "prefix": prefix_key}
        if not recursive:
            params["delimiter"] = "/"
        # Use bucket root.
        url = f"{self._endpoint.rstrip('/')}/{quote(self._bucket)}"
        resp = self._request("GET", url, params=params)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        entries: list[StorageEntry] = []
        # CommonPrefixes for dirs.
        for cp in root.findall(".//{*}CommonPrefixes/{*}Prefix"):
            pfx = cp.text or ""
            logical = "/" + pfx
            if self._prefix and logical.startswith("/" + self._prefix):
                logical = logical[len("/" + self._prefix) :]
                logical = _clean_posix(logical)
            entries.append(StorageEntry(path=_clean_posix(logical), is_dir=True))
        for obj in root.findall(".//{*}Contents"):
            key_el = obj.find("{*}Key")
            if key_el is None or not key_el.text:
                continue
            k = key_el.text
            if k.endswith("/") and not recursive:
                continue
            logical = "/" + k
            if self._prefix and logical.startswith("/" + self._prefix):
                logical = logical[len("/" + self._prefix) :]
                logical = _clean_posix(logical)
            if logical == _clean_posix(path):
                continue
            entries.append(StorageEntry(path=_clean_posix(logical), is_dir=False))
        return entries

    def copy_path(self, src: str, dst: str, *, overwrite: bool = False) -> None:
        # Use S3 server-side copy where possible.
        """Copy path."""
        src_key = self._key(src)
        dst_key = self._key(dst)
        dst_url = self._object_url(dst_key)
        headers = {"x-amz-copy-source": f"/{self._bucket}/{src_key}"}
        if not overwrite:
            headers["x-amz-copy-source-if-none-match"] = "*"
        resp = self._request("PUT", dst_url, headers=headers, data=b"")
        if resp.status_code == 412 and not overwrite:
            raise FileExistsError(dst)
        resp.raise_for_status()

    def move_path(self, src: str, dst: str, *, overwrite: bool = False) -> None:
        """Move path."""
        self.copy_path(src, dst, overwrite=overwrite)
        self.delete_path(src, missing_ok=False)

    def create_dir(
        self, path: str, *, parents: bool = True, exist_ok: bool = True
    ) -> None:
        # Directory semantics don't apply to S3; treat as not supported.
        """Create dir."""
        raise NotSupportedError("create_dir", backend=self.backend_name)

    def chmod_path(self, path: str, mode: int, *, recursive: bool = False) -> None:
        """Execute chmod path."""
        raise NotSupportedError("chmod_path", backend=self.backend_name)
