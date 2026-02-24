from __future__ import annotations

from pathlib import Path

import yaml

from tests.remote_env_helpers import merged_remote_env


def test_merged_remote_env_reads_google_oauth_from_profile_config(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    private_dir = tmp_path / "private"
    run_dir.mkdir(parents=True)
    private_dir.mkdir(parents=True)

    (run_dir / "env.remote-storage.base").write_text(
        "FILE_MCP_STORAGE_BACKEND=google_drive\n",
        encoding="utf-8",
    )
    (private_dir / "env-remote-storage").write_text(
        "\n".join(
            [
                "FILE_MCP_GDRIVE_CLIENT_ID=${vault.dev.storage.google_drive.client_id}",
                "FILE_MCP_GDRIVE_CLIENT_SECRET=${vault.dev.storage.google_drive.client_secret}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    config = {
        "profiles": {
            "default": {
                "storage": {
                    "backend": "google_drive",
                    "google_drive": {
                        "client_id": "cfg-client-id",
                        "client_secret": "cfg-client-secret",
                        "folder_id": "cfg-folder-id",
                        "refresh_token": "cfg-refresh-token",
                    },
                }
            }
        }
    }
    (tmp_path / "config.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
    )

    env = merged_remote_env(tmp_path, include_google=True)

    assert env["FILE_MCP_GDRIVE_CLIENT_ID"] == "cfg-client-id"
    assert env["FILE_MCP_GDRIVE_CLIENT_SECRET"] == "cfg-client-secret"
    assert env["FILE_MCP_GDRIVE_FOLDER_ID"] == "cfg-folder-id"
    assert env["FILE_MCP_GDRIVE_REFRESH_TOKEN"] == "cfg-refresh-token"
