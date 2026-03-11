from __future__ import annotations

import asyncio
import json
from pathlib import Path
from tests.path_helpers import project_root

import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.http_integration_helpers import (
    pick_free_port,
    running_server,
    wait_for_health,
)


def _decode_result(result):
    structured = getattr(result, "structuredContent", None)
    if structured not in (None, {}):
        return structured
    text = "\n".join(item.text for item in result.content if hasattr(item, "text"))
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _write_multi_profile_config(
    base_dir: Path, *, port: int
) -> tuple[Path, Path, Path, Path]:
    defaults_path = base_dir / "defaults.yaml"
    config_path = base_dir / "config.yaml"
    env_path = base_dir / "env"
    pidfile = base_dir / "server.pid"

    root_default = base_dir / "root-default"
    root_s3 = base_dir / "root-s3"
    root_webdav = base_dir / "root-webdav"
    root_ftp = base_dir / "root-ftp"
    root_gdrive = base_dir / "root-gdrive"
    for root in (root_default, root_s3, root_webdav, root_ftp, root_gdrive):
        root.mkdir(parents=True, exist_ok=True)

    (root_webdav / "private").mkdir(parents=True, exist_ok=True)
    (root_webdav / "private" / "hidden.txt").write_text("hidden", encoding="utf-8")
    (root_default / "outside.txt").write_text("outside", encoding="utf-8")

    config_text = """
profiles:
  default:
    auth:
      api_keys: ["${FILE_MCP_API_KEY_DEFAULT}"]
      header_name: "Authorization"
      header_scheme: "Bearer"
    storage:
      backend: local
    scope:
      roots: ["${FILE_MCP_ROOT_DEFAULT}"]
      allow_globs: ["**/*"]
      deny_globs: []
      allowed_exts: [".txt"]
      read_only_exts: []
    validation: {default_mode: "warn", per_type: {}}
    snapshots: {enabled: false, mode: "none", dir: "${FILE_MCP_SNAPSHOT_DIR}"}
    audit: {log_path: "${FILE_MCP_AUDIT_LOG}", include_content_hashes: true}
    observability: {enabled: true, log_path: "${FILE_MCP_SERVER_LOG}", level: "INFO"}
    limits: {search_max_results: 50, search_max_file_mb: 2, search_timeout_s: 10, storage_timeout_s: 10, conversion_timeout_s: 10}
    conversion: {enabled: true, backends: [], max_input_mb: 25}
  s3:
    auth:
      api_keys: ["${FILE_MCP_API_KEY_S3}"]
      header_name: "Authorization"
      header_scheme: "Bearer"
    storage:
      backend: local
    scope:
      roots: ["${FILE_MCP_ROOT_S3}"]
      allow_globs: ["**/*"]
      deny_globs: []
      allowed_exts: []
      read_only_exts: [".md"]
    validation: {default_mode: "warn", per_type: {}}
    snapshots: {enabled: false, mode: "none", dir: "${FILE_MCP_SNAPSHOT_DIR}"}
    audit: {log_path: "${FILE_MCP_AUDIT_LOG}", include_content_hashes: true}
    observability: {enabled: true, log_path: "${FILE_MCP_SERVER_LOG}", level: "INFO"}
    limits: {search_max_results: 50, search_max_file_mb: 2, search_timeout_s: 10, storage_timeout_s: 10, conversion_timeout_s: 10}
    conversion: {enabled: true, backends: [], max_input_mb: 25}
  webdav:
    auth:
      api_keys: ["${FILE_MCP_API_KEY_WEBDAV}"]
      header_name: "Authorization"
      header_scheme: "Bearer"
    storage:
      backend: local
    scope:
      roots: ["${FILE_MCP_ROOT_WEBDAV}"]
      allow_globs: ["**/*"]
      deny_globs: ["**/private/**"]
      allowed_exts: []
      read_only_exts: []
    validation: {default_mode: "warn", per_type: {}}
    snapshots: {enabled: false, mode: "none", dir: "${FILE_MCP_SNAPSHOT_DIR}"}
    audit: {log_path: "${FILE_MCP_AUDIT_LOG}", include_content_hashes: true}
    observability: {enabled: true, log_path: "${FILE_MCP_SERVER_LOG}", level: "INFO"}
    limits: {search_max_results: 50, search_max_file_mb: 2, search_timeout_s: 10, storage_timeout_s: 10, conversion_timeout_s: 10}
    conversion: {enabled: true, backends: [], max_input_mb: 25}
  ftp:
    auth:
      api_keys: ["${FILE_MCP_API_KEY_FTP}"]
      header_name: "Authorization"
      header_scheme: "Bearer"
    storage:
      backend: local
    scope:
      roots: ["${FILE_MCP_ROOT_FTP}"]
      allow_globs: ["**/*"]
      deny_globs: []
      allowed_exts: [".json"]
      read_only_exts: []
    validation: {default_mode: "warn", per_type: {}}
    snapshots: {enabled: false, mode: "none", dir: "${FILE_MCP_SNAPSHOT_DIR}"}
    audit: {log_path: "${FILE_MCP_AUDIT_LOG}", include_content_hashes: true}
    observability: {enabled: true, log_path: "${FILE_MCP_SERVER_LOG}", level: "INFO"}
    limits: {search_max_results: 50, search_max_file_mb: 2, search_timeout_s: 10, storage_timeout_s: 10, conversion_timeout_s: 10}
    conversion: {enabled: true, backends: [], max_input_mb: 25}
  google_drive:
    auth:
      api_keys: ["${FILE_MCP_API_KEY_GDRIVE}"]
      header_name: "Authorization"
      header_scheme: "Bearer"
    storage:
      backend: local
    scope:
      roots: ["${FILE_MCP_ROOT_GDRIVE}"]
      allow_globs: ["**/*"]
      deny_globs: []
      allowed_exts: [".txt"]
      read_only_exts: [".cfg"]
    validation: {default_mode: "warn", per_type: {}}
    snapshots: {enabled: false, mode: "none", dir: "${FILE_MCP_SNAPSHOT_DIR}"}
    audit: {log_path: "${FILE_MCP_AUDIT_LOG}", include_content_hashes: true}
    observability: {enabled: true, log_path: "${FILE_MCP_SERVER_LOG}", level: "INFO"}
    limits: {search_max_results: 50, search_max_file_mb: 2, search_timeout_s: 10, storage_timeout_s: 10, conversion_timeout_s: 10}
    conversion: {enabled: true, backends: [], max_input_mb: 25}
http:
  transport: "streamable-http"
  host: "127.0.0.1"
  port: "${FILE_MCP_HTTP_PORT}"
  base_path: "/"
  mcp_path: "/mcp"
  health_path: "/health"
  events_path: "/events"
  stateless_http: "true"
""".lstrip()
    defaults_path.write_text(config_text, encoding="utf-8")
    config_path.write_text(config_text, encoding="utf-8")
    env_path.write_text(
        "\n".join(
            [
                "FILE_MCP_API_KEY_DEFAULT=key-default",
                "FILE_MCP_API_KEY_S3=key-s3",
                "FILE_MCP_API_KEY_WEBDAV=key-webdav",
                "FILE_MCP_API_KEY_FTP=key-ftp",
                "FILE_MCP_API_KEY_GDRIVE=key-gdrive",
                f"FILE_MCP_ROOT_DEFAULT={root_default}",
                f"FILE_MCP_ROOT_S3={root_s3}",
                f"FILE_MCP_ROOT_WEBDAV={root_webdav}",
                f"FILE_MCP_ROOT_FTP={root_ftp}",
                f"FILE_MCP_ROOT_GDRIVE={root_gdrive}",
                f"FILE_MCP_HTTP_PORT={port}",
                f"FILE_MCP_AUDIT_LOG={base_dir / 'audit.log.jsonl'}",
                f"FILE_MCP_SERVER_LOG={base_dir / 'server.log'}",
                f"FILE_MCP_SNAPSHOT_DIR={base_dir / 'snapshots'}",
                "FILE_MCP_PROFILE=default",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return defaults_path, config_path, env_path, pidfile


def test_multi_profile_selection_auth_and_scope_controls(tmp_path: Path) -> None:
    port = pick_free_port()
    defaults_path, config_path, env_path, pidfile = _write_multi_profile_config(
        tmp_path, port=port
    )
    repo_root = project_root(Path(__file__))

    with running_server(
        repo_root,
        defaults_path=defaults_path,
        config_path=config_path,
        env_path=env_path,
        pidfile=pidfile,
    ):
        wait_for_health(f"http://127.0.0.1:{port}/health")

        async def _flow() -> None:
            default_root = tmp_path / "root-default"
            s3_root = tmp_path / "root-s3"
            webdav_root = tmp_path / "root-webdav"
            ftp_root = tmp_path / "root-ftp"
            gdrive_root = tmp_path / "root-gdrive"

            # 1) Default fallback profile (no selector) with default key.
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={"Authorization": "Bearer key-default"},
                )
            ) as client:
                out = _decode_result(
                    await client.call_tool(
                        "write_file",
                        {"path": str(default_root / "ok.txt"), "content": "ok"},
                    )
                )
                assert out["ok"] is True

            # 2) Query selector -> s3 profile; enforce read_only_exts (.md).
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp?profile=s3",
                    headers={"Authorization": "Bearer key-s3"},
                )
            ) as client:
                with pytest.raises(Exception):
                    await client.call_tool(
                        "write_file",
                        {"path": str(s3_root / "deny.md"), "content": "blocked"},
                    )
                out = _decode_result(
                    await client.call_tool(
                        "write_file",
                        {"path": str(s3_root / "allow.txt"), "content": "ok"},
                    )
                )
                assert out["ok"] is True

            # 3) Header selector -> webdav profile; enforce deny_globs.
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp",
                    headers={
                        "Authorization": "Bearer key-webdav",
                        "X-File-MCP-Profile": "webdav",
                    },
                )
            ) as client:
                with pytest.raises(Exception):
                    await client.call_tool(
                        "read_file",
                        {"path": str(webdav_root / "private" / "hidden.txt")},
                    )
                out = _decode_result(
                    await client.call_tool(
                        "write_file",
                        {"path": str(webdav_root / "ok.txt"), "content": "ok"},
                    )
                )
                assert out["ok"] is True

            # 4) FTP profile allowed_exts only .json.
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp?profile=ftp",
                    headers={"Authorization": "Bearer key-ftp"},
                )
            ) as client:
                with pytest.raises(Exception):
                    await client.call_tool(
                        "write_file",
                        {"path": str(ftp_root / "bad.txt"), "content": "nope"},
                    )
                out = _decode_result(
                    await client.call_tool(
                        "write_file",
                        {"path": str(ftp_root / "ok.json"), "content": '{"ok":true}'},
                    )
                )
                assert out["ok"] is True

            # 5) Google profile key routing + root restriction.
            async with Client(
                StreamableHttpTransport(
                    f"http://127.0.0.1:{port}/mcp?profile=google_drive",
                    headers={"Authorization": "Bearer key-gdrive"},
                )
            ) as client:
                out = _decode_result(
                    await client.call_tool(
                        "write_file",
                        {"path": str(gdrive_root / "ok.txt"), "content": "ok"},
                    )
                )
                assert out["ok"] is True
                with pytest.raises(Exception):
                    await client.call_tool(
                        "read_file", {"path": str(default_root / "outside.txt")}
                    )

            # 6) Wrong key for selected profile must fail auth.
            with pytest.raises(Exception):
                async with Client(
                    StreamableHttpTransport(
                        f"http://127.0.0.1:{port}/mcp?profile=ftp",
                        headers={"Authorization": "Bearer key-default"},
                    )
                ) as client:
                    await client.call_tool(
                        "list_dir", {"path": str(ftp_root), "recursive": False}
                    )

        asyncio.run(_flow())
