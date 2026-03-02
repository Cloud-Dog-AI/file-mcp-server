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

import typer

from file_tools.config.adapter import get_profile, load_config
from file_tools.logging_adapter import configure_logging_for_profile
from file_mcp_server.lifecycle import start_pidfile, status_pidfile, stop_pidfile
from file_mcp_server.server import run_fastmcp_http_server

app = typer.Typer(help="file-mcp-server CLI.")


def _default_pidfile() -> Path:
    return Path(".run") / "file-mcp-server.pid"


@app.command()
def serve(
    profile: str = typer.Option("default", help="Config profile name."),
    env_path: str | None = typer.Option(None, help="Path to .env file."),
    config_path: str | None = typer.Option(None, help="Path to config.yaml."),
    defaults_path: str | None = typer.Option(None, help="Path to defaults.yaml."),
    pidfile: Path = typer.Option(_default_pidfile(), help="Path to PID file."),
    force_pidfile: bool = typer.Option(False, help="Overwrite existing PID file."),
) -> None:
    """Run the FastMCP HTTP/SSE server."""
    if env_path:
        os.environ["FILE_MCP_ACTIVE_ENV_PATH"] = str(
            Path(env_path).expanduser().resolve()
        )
    else:
        os.environ["FILE_MCP_ACTIVE_ENV_PATH"] = ""
    if config_path:
        os.environ["FILE_MCP_ACTIVE_CONFIG_PATH"] = str(
            Path(config_path).expanduser().resolve()
        )
    else:
        os.environ["FILE_MCP_ACTIVE_CONFIG_PATH"] = str(
            (Path.cwd() / "config.yaml").resolve()
        )
    if defaults_path:
        os.environ["FILE_MCP_ACTIVE_DEFAULTS_PATH"] = str(
            Path(defaults_path).expanduser().resolve()
        )
    else:
        os.environ["FILE_MCP_ACTIVE_DEFAULTS_PATH"] = str(
            (Path.cwd() / "defaults.yaml").resolve()
        )
    os.environ["FILE_MCP_ACTIVE_PROFILE"] = profile

    config = load_config(
        env_path=env_path,
        config_path=config_path,
        defaults_path=defaults_path,
    )
    os.environ["FILE_MCP_ACTIVE_PROFILE_NAMES"] = ",".join(config.profiles.keys())
    profile_config = get_profile(config, name=profile)
    logger = configure_logging_for_profile(profile_config)
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
                http_config=config.http,
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
) -> None:
    """Start the server in a background process."""
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
    app()


if __name__ == "__main__":
    main()
