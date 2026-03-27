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

"""CLI entrypoint for file-mcp-server.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: CLI entrypoint for server lifecycle and configuration inspection.
Requirements: NF1.3, NF1.6
Tasks: T16, T18
Architecture: 7.4 Observability, 13. POSIX Operational Recommendations
Tests: ST1.1, ST1.6
Recent Change History:
- 2026-02-05: Configure operational logger during serve startup.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from os import environ as runtime_env
from typing import Optional

import typer

from file_tools.config.adapter import get_profile, load_config
from file_tools.config.models import (
    ComponentServerConfig,
    HttpServerConfig,
    ServerConfig,
)
from file_tools.logging_adapter import configure_logging_for_profile
from file_mcp_server.lifecycle import start_pidfile, status_pidfile, stop_pidfile
from file_mcp_server.server import run_fastmcp_http_server

app = typer.Typer(help="file-mcp-server CLI.")
SERVER_ROLES = ("api", "web", "mcp", "a2a")


def _default_pidfile() -> Path:
    """Handle default pidfile."""
    return Path(".run") / "file-mcp-server.pid"


def _normalise_server_role(server_role: str) -> str:
    """Validate and normalise server role name."""
    role = server_role.strip().lower()
    if role not in SERVER_ROLES:
        raise typer.BadParameter(
            "Invalid --server-role value. Expected one of: api, web, mcp, a2a."
        )
    return role


def _component_for_role(config: ServerConfig, role: str) -> ComponentServerConfig:
    """Return component-level host/port config for a server role."""
    if role == "api":
        return config.api_server
    if role == "web":
        return config.web_server
    if role == "mcp":
        return config.mcp_server
    return config.a2a_server


def _to_bool(value: bool | str | None, *, default: bool) -> bool:
    """Parse bool-like config values with a safe default."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _resolve_role_http_config(config: ServerConfig, role: str) -> HttpServerConfig:
    """Build HTTP settings for a role by overlaying component host/port values."""
    resolved = config.http.model_copy(deep=True)
    component = _component_for_role(config, role)

    host = str(component.host or "").strip()
    if host:
        resolved.host = host

    if component.port not in (None, ""):
        resolved.port = component.port

    if role == "mcp":
        transport = str(component.transport or "").strip()
        if transport:
            resolved.transport = transport

    return resolved


@app.command()
def serve(
    profile: str = typer.Option("default", help="Config profile name."),
    env_path: str | None = typer.Option(None, help="Path to .env file."),
    config_path: str | None = typer.Option(None, help="Path to config.yaml."),
    defaults_path: str | None = typer.Option(None, help="Path to defaults.yaml."),
    pidfile: Path = typer.Option(_default_pidfile(), help="Path to PID file."),
    force_pidfile: bool = typer.Option(False, help="Overwrite existing PID file."),
    server_role: Optional[str] = typer.Option(
        None, help="Server role: api|web|mcp|a2a. Omit for legacy single-server mode."
    ),
) -> None:
    """Run the FastMCP HTTP/SSE server."""
    resolved_role = _normalise_server_role(server_role) if server_role else None
    if env_path:
        runtime_env["FILE_MCP_ACTIVE_ENV_PATH"] = str(
            Path(env_path).expanduser().resolve()
        )
    else:
        runtime_env["FILE_MCP_ACTIVE_ENV_PATH"] = ""
    if config_path:
        runtime_env["FILE_MCP_ACTIVE_CONFIG_PATH"] = str(
            Path(config_path).expanduser().resolve()
        )
    else:
        runtime_env["FILE_MCP_ACTIVE_CONFIG_PATH"] = str(
            (Path.cwd() / "config.yaml").resolve()
        )
    if defaults_path:
        runtime_env["FILE_MCP_ACTIVE_DEFAULTS_PATH"] = str(
            Path(defaults_path).expanduser().resolve()
        )
    else:
        runtime_env["FILE_MCP_ACTIVE_DEFAULTS_PATH"] = str(
            (Path.cwd() / "defaults.yaml").resolve()
        )
    runtime_env["FILE_MCP_ACTIVE_PROFILE"] = profile
    runtime_env["FILE_MCP_ACTIVE_SERVER_ROLE"] = resolved_role or "legacy"

    config = load_config(
        env_path=env_path,
        config_path=config_path,
        defaults_path=defaults_path,
    )
    runtime_env["FILE_MCP_ACTIVE_PROFILE_NAMES"] = ",".join(config.profiles.keys())
    profile_config = get_profile(config, name=profile)
    logger = configure_logging_for_profile(profile_config)
    if resolved_role:
        component = _component_for_role(config, resolved_role)
        if not _to_bool(component.enabled, default=True):
            typer.echo(f"server role '{resolved_role}' is disabled in config")
            raise typer.Exit(1)
    current_pid = os.getpid()

    existing = status_pidfile(pidfile)
    if existing.running and existing.pid != current_pid and not force_pidfile:
        typer.echo(
            f"PID file already owned by running process {existing.pid}. Use --force-pidfile."
        )
        raise typer.Exit(1)

    start_pidfile(pidfile, pid=current_pid, force=True)
    logger.info("Server process started", pid=current_pid)
    try:
        asyncio.run(
            run_fastmcp_http_server(
                default_profile_name=profile,
                config=config,
                http_config=(
                    _resolve_role_http_config(config, resolved_role)
                    if resolved_role
                    else config.http
                ),
                logger=logger,
            )
        )
    finally:
        stop_pidfile(pidfile, send_signal=False)
        logger.info("Server process shutdown complete", pid=current_pid)


@app.command()
def start(
    profile: str = typer.Option("default", help="Config profile name."),
    env_path: str | None = typer.Option(None, help="Path to .env file."),
    config_path: str | None = typer.Option(None, help="Path to config.yaml."),
    defaults_path: str | None = typer.Option(None, help="Path to defaults.yaml."),
    pidfile: Path = typer.Option(_default_pidfile(), help="Path to PID file."),
    force: bool = typer.Option(False, help="Overwrite existing PID file."),
    server_role: Optional[str] = typer.Option(
        None, help="Server role: api|web|mcp|a2a. Omit for legacy single-server mode."
    ),
) -> None:
    """Start the server in a background process."""
    resolved_role = _normalise_server_role(server_role) if server_role else None
    status = status_pidfile(pidfile)
    if status.running and not force:
        typer.echo(status.message)
        raise typer.Exit(1)

    cmd = [
        sys.executable,
        "-m",
        "file_mcp_server",
        "serve",
        "--profile",
        profile,
        "--pidfile",
        str(pidfile),
        "--force-pidfile",
    ]
    if resolved_role:
        cmd.extend(["--server-role", resolved_role])
    if env_path:
        cmd.extend(["--env-path", env_path])
    if config_path:
        cmd.extend(["--config-path", config_path])
    if defaults_path:
        cmd.extend(["--defaults-path", defaults_path])

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    # Strict config + vault resolution can take several seconds on busy hosts.
    for _ in range(300):
        if process.poll() is not None:
            typer.echo("failed to start: serve process exited early")
            raise typer.Exit(1)
        current = status_pidfile(pidfile)
        if current.running and current.pid == process.pid:
            typer.echo(f"started (pid {process.pid})")
            return
        time.sleep(0.1)

    typer.echo("failed to start: timeout waiting for pidfile")
    raise typer.Exit(1)


@app.command()
def stop(
    pidfile: Path = typer.Option(_default_pidfile(), help="Path to PID file."),
    send_signal: bool = typer.Option(True, help="Send SIGTERM to PID before removing."),
) -> None:
    """Remove PID file and optionally signal the process."""
    status = stop_pidfile(pidfile, send_signal=send_signal)
    typer.echo(status.message)


@app.command()
def status(
    pidfile: Path = typer.Option(_default_pidfile(), help="Path to PID file."),
) -> None:
    """Check whether the server PID file is running."""
    status = status_pidfile(pidfile)
    typer.echo(status.message)


def main() -> None:
    """Execute main."""
    app()


if __name__ == "__main__":
    main()
