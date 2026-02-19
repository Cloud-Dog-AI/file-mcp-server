from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

import yaml
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from tests.http_integration_helpers import pick_free_port, running_server, wait_for_health
from tests.remote_env_helpers import file_mcp_env_values, merged_remote_env, write_env_file


def get_google_env_from_container() -> dict[str, str]:
    raw = subprocess.check_output(
        ["docker", "exec", "file-mcp-gdrive-auth", "sh", "-lc", "cat /app/config.yaml"],
        text=True,
    )
    cfg = yaml.safe_load(raw)
    gd = cfg["profiles"]["default"]["storage"]["google_drive"]
    return {
        "FILE_MCP_GDRIVE_USER_EMAIL": gd.get("user_email", ""),
        "FILE_MCP_GDRIVE_FOLDER_ID": gd.get("folder_id", ""),
        "FILE_MCP_GDRIVE_FOLDER_URL": gd.get("folder_url", ""),
        "FILE_MCP_GDRIVE_CLIENT_ID": gd.get("client_id", ""),
        "FILE_MCP_GDRIVE_CLIENT_SECRET": gd.get("client_secret", ""),
        "FILE_MCP_GDRIVE_REFRESH_TOKEN": gd.get("refresh_token", ""),
        "FILE_MCP_GDRIVE_ACCESS_TOKEN": gd.get("access_token", ""),
        "FILE_MCP_GDRIVE_REDIRECT_URI": gd.get("redirect_uri", ""),
        "FILE_MCP_GDRIVE_TOKEN_URI": gd.get("token_uri", "https://oauth2.googleapis.com/token"),
    }


def is_not_supported(msg: str) -> bool:
    return "Not supported for backend" in msg


def is_optional_failure(tool: str, msg: str) -> bool:
    lowered = msg.lower()
    if tool == "meld_files":
        return True
    if tool == "convert_file":
        needles = [
            "backend",
            "converter",
            "pandoc",
            "soffice",
            "unsupported",
            "not available",
            "cannot handle",
            "timed out",
        ]
        return any(n in lowered for n in needles)
    return False


async def run_backend(backend: str, env_ctx: dict[str, str]) -> dict[str, dict[str, str]]:
    port = pick_free_port()
    run_id = uuid.uuid4().hex[:8]
    scope_root = f"/exhaustive-{backend}"
    base = f"{scope_root}/audit-{backend}-{run_id}"
    file_txt = f"{base}/a.txt"
    file_copy = f"{base}/copy.txt"
    file_move = f"{base}/moved.txt"
    file_renamed = f"{base}/renamed.txt"
    file_json = f"{base}/data.json"
    file_yaml = f"{base}/data.yaml"
    file_md = f"{base}/doc.md"
    file_xml = f"{base}/data.xml"
    file_html = f"{base}/data.html"
    file_b64 = f"{base}/decoded.txt"

    repo_root = Path.cwd()
    defaults_path = repo_root / "defaults.yaml"
    config_path = repo_root / "config.yaml"
    env_path = Path(tempfile.gettempdir()) / f"exhaustive-file-mcp-{backend}.env"
    write_env_file(env_path, file_mcp_env_values(env_ctx))
    extra_env: dict[str, str] = {
        "FILE_MCP_HTTP_PORT": str(port),
        "FILE_MCP_API_KEY_PRIMARY": env_ctx["FILE_MCP_API_KEY_PRIMARY"],
        "FILE_MCP_AUTH_HEADER_NAME": env_ctx.get("FILE_MCP_AUTH_HEADER_NAME", "Authorization"),
        "FILE_MCP_AUTH_HEADER_SCHEME": env_ctx.get("FILE_MCP_AUTH_HEADER_SCHEME", "Bearer"),
        "FILE_MCP_STORAGE_BACKEND": backend,
        "FILE_MCP_ROOT": scope_root,
        "FILE_MCP_AUDIT_LOG": f"./working/remote-storage/audit.exhaustive.{backend}.log.jsonl",
        "FILE_MCP_SERVER_LOG": f"./working/remote-storage/server.exhaustive.{backend}.log",
        "FILE_MCP_SNAPSHOT_DIR": f"./working/remote-storage/snapshots.exhaustive.{backend}",
        "FILE_MCP_STORAGE_TIMEOUT_S": env_ctx.get("FILE_MCP_STORAGE_TIMEOUT_S", "30"),
        "FILE_MCP_SEARCH_TIMEOUT_S": env_ctx.get("FILE_MCP_SEARCH_TIMEOUT_S", "30"),
        "FILE_MCP_SEARCH_MAX_RESULTS": env_ctx.get("FILE_MCP_SEARCH_MAX_RESULTS", "250"),
        "FILE_MCP_SEARCH_MAX_FILE_MB": env_ctx.get("FILE_MCP_SEARCH_MAX_FILE_MB", "5"),
    }
    if backend == "webdav":
        extra_env.update(
            {
                "FILE_MCP_WEBDAV_BASE_URL": env_ctx["FILE_MCP_WEBDAV_BASE_URL"],
                "FILE_MCP_WEBDAV_USERNAME": env_ctx["FILE_MCP_WEBDAV_USERNAME"],
                "FILE_MCP_WEBDAV_PASSWORD": env_ctx["FILE_MCP_WEBDAV_PASSWORD"],
            }
        )
    elif backend == "ftp":
        extra_env.update(
            {
                "FILE_MCP_FTP_HOST": env_ctx["FILE_MCP_FTP_HOST"],
                "FILE_MCP_FTP_PORT": env_ctx.get("FILE_MCP_FTP_PORT", "21"),
                "FILE_MCP_FTP_USERNAME": env_ctx["FILE_MCP_FTP_USERNAME"],
                "FILE_MCP_FTP_PASSWORD": env_ctx["FILE_MCP_FTP_PASSWORD"],
                "FILE_MCP_FTP_BASE_DIR": env_ctx.get("FILE_MCP_FTP_BASE_DIR", "/"),
                "FILE_MCP_FTP_USE_TLS": env_ctx.get("FILE_MCP_FTP_USE_TLS", "false"),
            }
        )
    elif backend == "s3":
        extra_env.update(
            {
                "FILE_MCP_S3_ENDPOINT": env_ctx["FILE_MCP_S3_ENDPOINT"],
                "FILE_MCP_S3_BUCKET": env_ctx["FILE_MCP_S3_BUCKET"],
                "FILE_MCP_S3_REGION": env_ctx.get("FILE_MCP_S3_REGION", "us-east-1"),
                "FILE_MCP_S3_ACCESS_KEY": env_ctx["FILE_MCP_S3_ACCESS_KEY"],
                "FILE_MCP_S3_SECRET_KEY": env_ctx["FILE_MCP_S3_SECRET_KEY"],
                "FILE_MCP_S3_PREFIX": f"file-mcp-exhaustive/{run_id}",
            }
        )
    elif backend == "google_drive":
        extra_env.update(
            {
                "FILE_MCP_GDRIVE_USER_EMAIL": env_ctx.get("FILE_MCP_GDRIVE_USER_EMAIL", ""),
                "FILE_MCP_GDRIVE_FOLDER_ID": env_ctx.get("FILE_MCP_GDRIVE_FOLDER_ID", ""),
                "FILE_MCP_GDRIVE_FOLDER_URL": env_ctx.get("FILE_MCP_GDRIVE_FOLDER_URL", ""),
                "FILE_MCP_GDRIVE_CLIENT_ID": env_ctx["FILE_MCP_GDRIVE_CLIENT_ID"],
                "FILE_MCP_GDRIVE_CLIENT_SECRET": env_ctx["FILE_MCP_GDRIVE_CLIENT_SECRET"],
                "FILE_MCP_GDRIVE_REFRESH_TOKEN": env_ctx.get("FILE_MCP_GDRIVE_REFRESH_TOKEN", ""),
                "FILE_MCP_GDRIVE_ACCESS_TOKEN": env_ctx.get("FILE_MCP_GDRIVE_ACCESS_TOKEN", ""),
                "FILE_MCP_GDRIVE_REDIRECT_URI": env_ctx.get("FILE_MCP_GDRIVE_REDIRECT_URI", "urn:ietf:wg:oauth:2.0:oob"),
                "FILE_MCP_GDRIVE_TOKEN_URI": env_ctx.get("FILE_MCP_GDRIVE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
            }
        )

    Path("./working/remote-storage").mkdir(parents=True, exist_ok=True)
    results: dict[str, dict[str, str]] = {}

    with running_server(
        repo_root,
        defaults_path=defaults_path,
        config_path=config_path,
        env_path=env_path,
        pidfile=Path(tempfile.gettempdir()) / f"exhaust-{backend}.pid",
        extra_env=extra_env,
    ):
        wait_for_health(f"http://127.0.0.1:{port}/health", timeout_s=25.0)

        async with Client(
            StreamableHttpTransport(
                f"http://127.0.0.1:{port}/mcp",
                headers={"Authorization": f"Bearer {env_ctx['FILE_MCP_API_KEY_PRIMARY']}"},
            )
        ) as client:
            tool_names = [t.name for t in await client.list_tools()]

            call_timeout = float(os.getenv("FILE_MCP_EXHAUSTIVE_TOOL_TIMEOUT_S", "12"))

            async def call(tool: str, args: dict) -> tuple[str, str]:
                try:
                    await asyncio.wait_for(client.call_tool(tool, args), timeout=call_timeout)
                    return "pass", ""
                except asyncio.TimeoutError:
                    return "fail", f"tool call timed out after {int(call_timeout)}s"
                except Exception as exc:  # pragma: no cover - integration runtime
                    msg = str(exc)
                    if is_not_supported(msg):
                        return "not_supported", msg
                    if is_optional_failure(tool, msg):
                        return "optional_fail", msg
                    return "fail", msg

            status, message = await call("create_dir", {"path": base, "parents": True, "exist_ok": True})
            results["create_dir"] = {"status": status, "msg": message}
            status, message = await call("write_file", {"path": file_txt, "content": f"hello {backend} {run_id}\n"})
            results["write_file"] = {"status": status, "msg": message}

            await call("write_file", {"path": file_json, "content": "{\"x\":1}\n"})
            await call("write_file", {"path": file_yaml, "content": "root:\n  a: 1\n"})
            await call("write_file", {"path": file_md, "content": "# Title\n\nBody\n"})
            await call("write_file", {"path": file_xml, "content": "<root><item>1</item></root>\n"})
            await call("write_file", {"path": file_html, "content": "<html><body><p id='m'>x</p></body></html>\n"})

            calls: dict[str, dict] = {
                "read_file": {"path": file_txt},
                "delete_file": {"path": f"{base}/missing.txt", "missing_ok": True},
                "copy_file": {"src": file_txt, "dst": file_copy, "overwrite": True},
                "chmod_path": {"path": file_txt, "mode": "0644"},
                "move_file": {"src": file_copy, "dst": file_move, "overwrite": True},
                "move_path": {"src": file_move, "dst": file_renamed, "overwrite": True},
                "rename_path": {"src": file_renamed, "dst": file_copy, "overwrite": True},
                "list_dir": {"path": base, "recursive": True},
                "search_paths": {"query": "data", "max_depth": 3, "timeout_s": 10},
                "search_content": {"query": run_id, "max_depth": 4, "timeout_s": 10, "max_results": 10},
                "diff_text": {"before": "a\n", "after": "b\n", "context": 1},
                "b64_encode": {"text": "hello"},
                "b64_decode": {"data": "aGVsbG8="},
                "b64_encode_file": {"path": file_txt},
                "validate_text": {"content_type": "json", "text": "{\"a\":1}"},
                "validate_file": {"path": file_json},
                "json_get": {"text": "{\"x\":1}", "path": "/x"},
                "json_set": {"text": "{\"x\":1}", "path": "/y", "value": 2},
                "json_delete": {"text": "{\"x\":1}", "path": "/x"},
                "json_copy": {"text": "{\"x\":1}", "from_path": "/x", "to_path": "/y"},
                "json_move": {"text": "{\"x\":1}", "from_path": "/x", "to_path": "/y"},
                "json_merge": {"text": "{\"x\":1}", "path": "/", "value": {"y": 2}},
                "yaml_get": {"text": "root:\n  a: 1\n", "path": "/root/a"},
                "yaml_set": {"text": "root:\n  a: 1\n", "path": "/root/b", "value": 2},
                "yaml_delete": {"text": "root:\n  a: 1\n", "path": "/root/a"},
                "yaml_copy": {"text": "root:\n  a: 1\n", "from_path": "/root/a", "to_path": "/root/b"},
                "yaml_move": {"text": "root:\n  a: 1\n", "from_path": "/root/a", "to_path": "/root/b"},
                "yaml_merge": {"text": "root:\n  a: 1\n", "path": "/root", "value": {"b": 2}},
                "markdown_get_section": {"text": "# Title\n\nBody\n", "heading": "Title"},
                "markdown_set_section": {"text": "# Title\n\nBody\n", "heading": "Title", "new_content": "Updated"},
                "replace_regex": {"text": "abc", "pattern": "a", "repl": "z", "count": 1},
                "diff_files": {"path_a": file_txt, "path_b": file_copy},
                "meld_files": {"path_a": file_txt, "path_b": file_copy},
                "json_set_file": {"path": file_json, "json_path": "/y", "value": 2},
                "json_copy_file": {"path": file_json, "from_path": "/y", "to_path": "/z"},
                "json_move_file": {"path": file_json, "from_path": "/z", "to_path": "/moved"},
                "json_merge_file": {"path": file_json, "json_path": "/", "value": {"k": "v"}},
                "xml_set_file": {"path": file_xml, "xpath": "/root/item", "value": "2"},
                "yaml_set_file": {"path": file_yaml, "yaml_path": "/root/b", "value": 2},
                "yaml_delete_file": {"path": file_yaml, "yaml_path": "/root/a"},
                "yaml_copy_file": {"path": file_yaml, "from_path": "/root/b", "to_path": "/root/c"},
                "yaml_move_file": {"path": file_yaml, "from_path": "/root/c", "to_path": "/root/d"},
                "html_set_file": {"path": file_html, "selector": "#m", "value": "y"},
                "markdown_set_section_file": {"path": file_md, "heading": "Title", "new_content": "Updated body"},
                "markdown_set_frontmatter_file": {"path": file_md, "updates": {"owner": "matrix"}},
                "convert_file": {"path": file_md, "target_format": "text", "timeout_s": 15},
                "json_get_file": {"path": file_json, "json_path": "/moved"},
                "yaml_get_file": {"path": file_yaml, "yaml_path": "/root/d"},
                "yaml_merge_file": {"path": file_yaml, "yaml_path": "/root", "value": {"e": 5}},
                "sed_edit_file": {"path": file_txt, "operations": [{"op": "replace_regex", "pattern": "hello", "repl": "hi"}]},
                "backend_status": {},
            }

            try:
                enc = await client.call_tool("b64_encode_file", {"path": file_txt})
                data = enc.data.get("data") if hasattr(enc, "data") else None
                calls["b64_decode_to_file"] = {"path": file_b64, "data": data or "aGVsbG8=", "overwrite": True}
            except Exception:
                calls["b64_decode_to_file"] = {"path": file_b64, "data": "aGVsbG8=", "overwrite": True}

            ordered_tools = [t for t in tool_names if t not in {"search_paths", "search_content"}] + [
                t for t in tool_names if t in {"search_paths", "search_content"}
            ]
            for tool in ordered_tools:
                if tool in results:
                    continue
                if tool not in calls:
                    results[tool] = {"status": "fail", "msg": "no test call mapping"}
                    print(f"  {backend}:{tool}:fail:no test call mapping", flush=True)
                    continue
                status, message = await call(tool, calls[tool])
                results[tool] = {"status": status, "msg": message}
                print(f"  {backend}:{tool}:{status}", flush=True)

    return results


async def main() -> None:
    repo_root = Path.cwd()
    env_ctx = merged_remote_env(repo_root, include_google=True)
    env_ctx.update(get_google_env_from_container())

    selected = (os.getenv("FILE_MCP_EXHAUSTIVE_BACKENDS", "") or "").strip()
    if selected:
        backends = [part.strip() for part in selected.split(",") if part.strip()]
    else:
        backends = ["webdav", "ftp", "s3", "google_drive"]
    summary: dict[str, dict[str, dict[str, str]]] = {}
    for backend in backends:
        print(f"RUN_BACKEND={backend}", flush=True)
        summary[backend] = await run_backend(backend, env_ctx)

    Path("working").mkdir(exist_ok=True)
    report = Path("working/exhaustive_backend_tool_audit.json")
    report.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    for backend, data in summary.items():
        counts = {"pass": 0, "not_supported": 0, "optional_fail": 0, "fail": 0}
        for result in data.values():
            counts[result["status"]] = counts.get(result["status"], 0) + 1
        print(
            f"{backend}: pass={counts['pass']} not_supported={counts['not_supported']} optional_fail={counts['optional_fail']} fail={counts['fail']}"
        )
        failed_tools = [name for name, result in data.items() if result["status"] == "fail"]
        if failed_tools:
            print("  FAIL_TOOLS:", ", ".join(failed_tools))

    print(f"REPORT={report}")


if __name__ == "__main__":
    asyncio.run(main())
