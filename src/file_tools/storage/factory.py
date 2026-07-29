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
file-mcp-server — file_tools/storage/factory.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Adapter between file-mcp ProfileConfig and cloud_dog_storage.

Delegates to cloud_dog_storage.build_storage_backend (PS-85) after
translating the service-specific ProfileConfig into a StorageConfig.
"""

from __future__ import annotations

from cloud_dog_storage import StorageBackend
from cloud_dog_storage import build_storage_backend as _platform_build
from cloud_dog_storage.config.models import (
    FtpConfig,
    GoogleDriveConfig,
    S3Config,
    StorageConfig,
    TlsConfig,
    WebDavConfig,
)
from cloud_dog_storage.errors import ConfigurationError

from file_tools.config.models import ProfileConfig


def _resolved_google_drive_value(value: object) -> str:
    """Return a usable Drive setting without ever forwarding a placeholder.

    Server profile values may arrive as ``${ENV_VAR}`` when the environment
    did not supply that variable.  The shared storage package treats any
    non-empty string as configured, so forwarding one would issue a request
    to the OAuth provider with the literal placeholder.  Keep that boundary
    fail-closed in FileMCP, where profile interpolation is owned.
    """
    text = str(value or "").strip()
    return "" if "${" in text else text


def _google_drive_config(profile: ProfileConfig) -> GoogleDriveConfig:
    """Build a validated Google Drive adapter config from a service profile."""
    source = profile.storage.google_drive
    folder_id = _resolved_google_drive_value(source.folder_id if source else "")
    folder_url = _resolved_google_drive_value(source.folder_url if source else "")
    client_id = _resolved_google_drive_value(source.client_id if source else "")
    client_secret = _resolved_google_drive_value(source.client_secret if source else "")
    refresh_token = _resolved_google_drive_value(source.refresh_token if source else "")
    access_token = _resolved_google_drive_value(source.access_token if source else "")
    token_uri = _resolved_google_drive_value(source.token_uri if source else "")

    missing: list[str] = []
    if not folder_id and not folder_url:
        missing.append("google_drive.folder_id or google_drive.folder_url")
    if not client_id:
        missing.append("google_drive.client_id")
    if not client_secret:
        missing.append("google_drive.client_secret")
    if not refresh_token and not access_token:
        missing.append("google_drive.refresh_token or google_drive.access_token")
    if not token_uri:
        missing.append("google_drive.token_uri")
    if missing:
        raise ConfigurationError(
            "Google Drive storage requires resolved configuration: "
            + ", ".join(missing),
            backend_name="google_drive",
        )

    return GoogleDriveConfig(
        folder_id=folder_id,
        folder_url=folder_url,
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
        access_token=access_token,
        redirect_uri=_resolved_google_drive_value(
            source.redirect_uri if source else ""
        ),
        token_uri=token_uri,
    )


def build_storage_backend(profile: ProfileConfig) -> StorageBackend:
    """Build storage backend from a file-mcp ProfileConfig.

    Translates the service-level config into a platform StorageConfig
    and delegates to ``cloud_dog_storage.build_storage_backend``.
    """
    src = profile.storage
    timeout = int(profile.limits.storage_timeout_s or 30)
    backend_name = (src.backend or "local").strip().lower()

    # For local backend, file-mcp handles path scoping itself via
    # scope.roots enforcement in the tool layer.  Pass "/" as root so
    # the platform LocalStorage accepts absolute paths.
    if backend_name in {"", "local", "filesystem", "fs"}:
        root_path = "/"
    else:
        root_path = ""

    google_drive = (
        _google_drive_config(profile)
        if backend_name
        in {
            "google_drive",
            "gdrive",
            "drive",
        }
        else GoogleDriveConfig(
            folder_id=str(src.google_drive.folder_id or "") if src.google_drive else "",
            folder_url=str(src.google_drive.folder_url or "")
            if src.google_drive
            else "",
            client_id=str(src.google_drive.client_id or "") if src.google_drive else "",
            client_secret=str(src.google_drive.client_secret or "")
            if src.google_drive
            else "",
            refresh_token=str(src.google_drive.refresh_token or "")
            if src.google_drive
            else "",
            access_token=str(src.google_drive.access_token or "")
            if src.google_drive
            else "",
            redirect_uri=str(src.google_drive.redirect_uri or "")
            if src.google_drive
            else "",
            token_uri=str(src.google_drive.token_uri or "") if src.google_drive else "",
        )
    )

    storage_cfg = StorageConfig(
        backend=backend_name,
        root_path=root_path,
        timeout_s=timeout,
        tls=TlsConfig(
            insecure_skip_verify=bool(src.tls.insecure_skip_verify)
            if src.tls
            else False,
            ca_bundle_path=str(src.tls.ca_bundle_path or "") if src.tls else "",
        ),
        s3=S3Config(
            endpoint=str(src.s3.endpoint or "") if src.s3 else "",
            bucket=str(src.s3.bucket or "") if src.s3 else "",
            region=str(src.s3.region or "") if src.s3 else "",
            access_key=str(src.s3.access_key or "") if src.s3 else "",
            secret_key=str(src.s3.secret_key or "") if src.s3 else "",
            prefix=str(src.s3.prefix or "") if src.s3 else "",
        ),
        webdav=WebDavConfig(
            base_url=str(src.webdav.base_url or "") if src.webdav else "",
            username=str(src.webdav.username or "") if src.webdav else "",
            password=str(src.webdav.password or "") if src.webdav else "",
        ),
        ftp=FtpConfig(
            host=str(src.ftp.host or "") if src.ftp else "",
            port=int(src.ftp.port or 21) if src.ftp else 21,
            username=str(src.ftp.username or "") if src.ftp else "",
            password=str(src.ftp.password or "") if src.ftp else "",
        ),
        google_drive=google_drive,
    )

    return _platform_build(storage_cfg)
