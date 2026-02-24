from __future__ import annotations

from pathlib import Path

from tests.config_helpers import build_profile
from file_tools.audit import AuditEvent, AuditLogger, build_event, create_snapshot


def _build_profile(tmp_path: Path, *, log_path: Path, snapshot_dir: Path):
    defaults_yaml = """
profiles:
  default:
    audit:
      log_path: "${FILE_MCP_AUDIT_LOG}"
    snapshots:
      dir: "${FILE_MCP_SNAPSHOT_DIR}"
""".lstrip()
    config_yaml = defaults_yaml
    env_values = {
        "FILE_MCP_AUDIT_LOG": str(log_path),
        "FILE_MCP_SNAPSHOT_DIR": str(snapshot_dir),
    }
    return build_profile(
        tmp_path,
        env_values=env_values,
        defaults_yaml=defaults_yaml,
        config_yaml=config_yaml,
    )


def test_build_event() -> None:
    event = build_event(tool="read", action="read_file", status="ok")
    assert isinstance(event, AuditEvent)
    assert event.tool == "read"


def test_audit_logger_writes(tmp_path: Path) -> None:
    log_path = tmp_path / "audit.log"
    snapshot_dir = tmp_path / "snapshots"
    profile = _build_profile(tmp_path, log_path=log_path, snapshot_dir=snapshot_dir)
    logger = AuditLogger(Path(profile.audit.log_path))
    event = build_event(tool="write", action="write_file", status="ok")
    logger.write(event)
    content = log_path.read_text()
    assert "write_file" in content


def test_create_snapshot(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("data")
    log_path = tmp_path / "audit.log"
    snapshot_dir = tmp_path / "snapshots"
    profile = _build_profile(tmp_path, log_path=log_path, snapshot_dir=snapshot_dir)
    dest = create_snapshot(Path(profile.snapshots.dir), source)
    assert dest.exists()
    assert dest.read_text() == "data"
