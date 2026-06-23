"""
Automated package compliance test.
This test FAILS if any bespoke code exists that should use a platform package.
It runs as part of QT - every CI/test run enforces compliance automatically.
"""

from __future__ import annotations

import pathlib
import subprocess

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"


def _has_web_server() -> bool:
    """Return True when this project exposes a web server/runtime-config surface."""
    legacy_web_root = PROJECT_ROOT / "src" / "servers" / "web"
    file_mcp_web_runtime = PROJECT_ROOT / "src" / "file_mcp_server" / "server_runtime.py"
    return legacy_web_root.exists() or file_mcp_web_runtime.exists()


def _grep_count(pattern: str, exclude_pattern: str | None = None) -> list[str]:
    """Grep src/ for a pattern, return matching file:line entries."""
    cmd = f"grep -rn '{pattern}' {SRC_DIR} --include='*.py'"
    if exclude_pattern:
        cmd += f" | grep -v '{exclude_pattern}'"
    cmd += " | grep -v __pycache__"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return [line for line in result.stdout.strip().split("\n") if line]


class TestPackageCompliance:
    """Every test here MUST pass. Zero bespoke code allowed."""
    @pytest.mark.QT
    @pytest.mark.mcp
    @pytest.mark.req("NF-001")  # W28E-1802A: platform-package adoption (cloud_dog_* packages; no bespoke replacements) (rebound from W28C-1711-R3 probe)

    def test_no_bespoke_logging(self):
        """All logging must use cloud_dog_logging. Zero logging.getLogger calls."""
        hits = _grep_count("logging.getLogger", "cloud_dog")
        assert len(hits) == 0, (
            f"FAIL: {len(hits)} bespoke logging calls found. "
            f"Replace with cloud_dog_logging:\n" + "\n".join(hits[:10])
        )
    @pytest.mark.QT
    @pytest.mark.mcp
    @pytest.mark.req("NF-001")  # W28E-1802A: platform-package adoption (cloud_dog_* packages; no bespoke replacements) (rebound from W28C-1711-R3 probe)

    def test_no_bespoke_config_manager(self):
        """Config must use cloud_dog_config. Zero bespoke ConfigManager."""
        hits = _grep_count("ConfigManager|config_manager", "cloud_dog")
        real_hits = [h for h in hits if "cloud_dog_config" not in h]
        assert len(real_hits) == 0, (
            f"FAIL: {len(real_hits)} bespoke config calls found:\n"
            + "\n".join(real_hits[:10])
        )
    @pytest.mark.QT
    @pytest.mark.mcp
    @pytest.mark.req("NF-001")  # W28E-1802A: platform-package adoption (cloud_dog_* packages; no bespoke replacements) (rebound from W28C-1711-R3 probe)

    def test_no_bespoke_auth(self):
        """Auth must use cloud_dog_idam. Zero bespoke auth imports outside the package."""
        hits = _grep_count("from.*auth|import.*auth", "cloud_dog")
        real_hits = []
        for hit in hits:
            filepath = hit.split(":")[0]
            try:
                content = pathlib.Path(filepath).read_text()
                if "cloud_dog_idam" in content:
                    continue
            except Exception:
                pass
            real_hits.append(hit)
        assert len(real_hits) == 0, (
            "FAIL: "
            f"{len(real_hits)} bespoke auth imports not delegating to cloud_dog_idam:\n"
            + "\n".join(real_hits[:10])
        )
    @pytest.mark.QT
    @pytest.mark.mcp
    @pytest.mark.req("NF-001")  # W28E-1802A: platform-package adoption (cloud_dog_* packages; no bespoke replacements) (rebound from W28C-1711-R3 probe)

    def test_no_memory_queue(self):
        """Jobs must use cloud_dog_jobs. Zero MemoryQueue/ThreadPoolExecutor."""
        hits = _grep_count("MemoryQueue|ThreadPoolExecutor|asyncio.Queue", "cloud_dog")
        assert len(hits) == 0, (
            f"FAIL: {len(hits)} bespoke queue/thread calls found:\n"
            + "\n".join(hits[:10])
        )
    @pytest.mark.QT
    @pytest.mark.mcp
    @pytest.mark.req("NF-001")  # W28E-1802A: platform-package adoption (cloud_dog_* packages; no bespoke replacements) (rebound from W28C-1711-R3 probe)

    def test_no_direct_llm_calls(self):
        """LLM calls must use cloud_dog_llm. Zero direct httpx to ollama/openai."""
        hits = _grep_count(
            "httpx.AsyncClient.*ollama|requests.post.*ollama|openai.ChatCompletion",
            "cloud_dog",
        )
        assert len(hits) == 0, (
            f"FAIL: {len(hits)} direct LLM calls found:\n" + "\n".join(hits[:10])
        )
    @pytest.mark.QT
    @pytest.mark.mcp
    @pytest.mark.req("NF-001")  # W28E-1802A: platform-package adoption (cloud_dog_* packages; no bespoke replacements) (rebound from W28C-1711-R3 probe)

    def test_no_hardcoded_secrets(self):
        """Zero hardcoded passwords or secrets in source."""
        hits = _grep_count("password.*=.*['\"]|secret.*=.*['\"]|api_key.*=.*['\"]")
        real_hits = [
            hit
            for hit in hits
            if not any(
                marker in hit.lower()
                for marker in [
                    "test",
                    "example",
                    "placeholder",
                    "changeme",
                    "12345",
                    "os.environ",
                    "config.get",
                ]
            )
        ]
        assert len(real_hits) == 0, (
            f"FAIL: {len(real_hits)} hardcoded secrets found:\n"
            + "\n".join(real_hits[:10])
        )
    @pytest.mark.QT
    @pytest.mark.mcp
    @pytest.mark.req("NF-001")  # W28E-1802A: platform-package adoption (cloud_dog_* packages; no bespoke replacements) (rebound from W28C-1711-R3 probe)

    def test_no_internal_hostnames(self):
        """Zero internal hostnames in source (must use config/vault)."""
        hits = _grep_count("cloud-dog\\.net|viewdeck\\.com|vault0\\.|server0\\.|db1\\.app")
        real_hits = [
            hit
            for hit in hits
            if not any(
                marker in hit
                for marker in ["#", '"""', "vault.", "test", "PREPROD", "example", "docs/"]
            )
        ]
        assert len(real_hits) == 0, (
            f"FAIL: {len(real_hits)} internal hostnames in source:\n"
            + "\n".join(real_hits[:10])
        )
    @pytest.mark.QT
    @pytest.mark.mcp
    @pytest.mark.req("NF-001")  # W28E-1802A: platform-package adoption (cloud_dog_* packages; no bespoke replacements) (rebound from W28C-1711-R3 probe)

    def test_ui_dist_exists(self):
        """PS-30: ui/dist/ must exist (SPA built and wired)."""
        ui_dist = PROJECT_ROOT / "ui" / "dist"
        if not _has_web_server():
            pytest.skip("No web server - UI not applicable")
        assert ui_dist.exists(), "FAIL: ui/dist/ not found. SPA must be built."
    @pytest.mark.QT
    @pytest.mark.mcp
    @pytest.mark.req("NF-001")  # W28E-1802A: platform-package adoption (cloud_dog_* packages; no bespoke replacements) (rebound from W28C-1711-R3 probe)

    def test_runtime_config_endpoint(self):
        """PS-30: /runtime-config.js must be served by the web server."""
        web_files = list(SRC_DIR.rglob("*.py"))
        has_runtime_config = False
        for filepath in web_files:
            try:
                content = filepath.read_text()
            except Exception:
                continue
            if "runtime-config" in content or "runtime_config" in content:
                has_runtime_config = True
                break
        if not _has_web_server():
            pytest.skip("No web server - runtime-config not applicable")
        assert has_runtime_config, "FAIL: No /runtime-config.js endpoint found in web server."
    @pytest.mark.QT
    @pytest.mark.mcp
    @pytest.mark.req("NF-001")  # W28E-1802A: platform-package adoption (cloud_dog_* packages; no bespoke replacements) (rebound from W28C-1711-R3 probe)

    def test_server_control_exists(self):
        """server_control.sh must exist."""
        assert (PROJECT_ROOT / "server_control.sh").exists(), "FAIL: server_control.sh missing."
    @pytest.mark.QT
    @pytest.mark.mcp
    @pytest.mark.req("NF-001")  # W28E-1802A: platform-package adoption (cloud_dog_* packages; no bespoke replacements) (rebound from W28C-1711-R3 probe)

    def test_licence_exists(self):
        """LICENCE file must exist."""
        assert (PROJECT_ROOT / "LICENCE").exists(), "FAIL: LICENCE file missing."
    @pytest.mark.QT
    @pytest.mark.mcp
    @pytest.mark.req("NF-001")  # W28E-1802A: platform-package adoption (cloud_dog_* packages; no bespoke replacements) (rebound from W28C-1711-R3 probe)

    def test_readme_exists(self):
        """README.md must exist."""
        assert (PROJECT_ROOT / "README.md").exists(), "FAIL: README.md missing."
