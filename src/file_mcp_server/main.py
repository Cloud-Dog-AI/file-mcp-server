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

from pathlib import Path

import typer

from file_tools.config.loader import get_profile, load_config
from file_tools.observability import configure_operational_logger
from file_mcp_server.lifecycle import start_pidfile, status_pidfile, stop_pidfile

app = typer.Typer(help="file-mcp-server CLI (scaffold).")


def _default_pidfile() -> Path:
    return Path(".run") / "file-mcp-server.pid"


@app.command()
def serve(
    profile: str = typer.Option("default", help="Config profile name."),
    env_path: str | None = typer.Option(None, help="Path to .env file."),
    config_path: str | None = typer.Option(None, help="Path to config.yaml."),
    defaults_path: str | None = typer.Option(None, help="Path to defaults.yaml."),
) -> None:
    """Run the MCP server (not yet implemented)."""
    config = load_config(
        env_path=env_path,
        config_path=config_path,
        defaults_path=defaults_path,
    )
    profile_config = get_profile(config, name=profile)
    logger = configure_operational_logger(profile_config.observability)
    scope = profile_config.scope

    typer.echo("file-mcp-server scaffolding only. Server implementation pending.")
    logger.info("Loaded profile '%s' with %s roots.", profile, len(scope.roots))
    typer.echo(f"Profile: {profile}")
    typer.echo(f"Roots: {len(scope.roots)}")
    typer.echo(f"Allow globs: {', '.join(scope.allow_globs) if scope.allow_globs else '(none)'}")
    typer.echo(f"Deny globs: {', '.join(scope.deny_globs) if scope.deny_globs else '(none)'}")
    typer.echo(f"Allowed extensions: {', '.join(scope.allowed_exts) if scope.allowed_exts else '(none)'}")
    typer.echo(
        f"Read-only extensions: {', '.join(scope.read_only_exts) if scope.read_only_exts else '(none)'}"
    )


@app.command()
def start(
    pidfile: Path = typer.Option(_default_pidfile(), help="Path to PID file."),
    force: bool = typer.Option(False, help="Overwrite existing PID file."),
) -> None:
    """Write PID file to indicate the server is running."""
    status = start_pidfile(pidfile, force=force)
    typer.echo(status.message)


@app.command()
def stop(
    pidfile: Path = typer.Option(_default_pidfile(), help="Path to PID file."),
    send_signal: bool = typer.Option(False, help="Send SIGTERM to PID before removing."),
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
