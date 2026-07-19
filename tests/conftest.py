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

from pathlib import Path
import re
import sys
from functools import lru_cache

import pytest
from cloud_dog_config.compiler.vault_resolver import resolve_vault_identifier
from cloud_dog_config.vault.client import VaultClient, VaultConnectionConfig
from tests.env_runtime import runtime_env

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
_VAULT_REF_PATTERN = re.compile(r"^\$\{(vault\.[^}]+)\}$")
_OPTIONAL_TEST_ENV_KEYS = (
    "TEST_ENV_TIER",
    "TEST_WEB_BASE_PATH",
    "TEST_A2A_BASE_PATH",
    "CLOUD_DOG_DB__DIALECT",
    "CLOUD_DOG_DB__HOST",
    "CLOUD_DOG_DB__PORT",
    "CLOUD_DOG_DB__USERNAME",
    "CLOUD_DOG_DB__PASSWORD",
    "CLOUD_DOG_DB__DATABASE",
    "LOCAL_DOCKER_SOURCE_ENV",
    "LOCAL_DOCKER_COMPOSE_FILE",
    "LOCAL_DOCKER_PROJECT_NAME",
    "LOCAL_DOCKER_SERVICES",
)
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--env",
        action="store",
        default=None,
        help="Path to env file (e.g. tests/env-UT)",
    )


@lru_cache(maxsize=1)
def _vault_client() -> VaultClient | None:
    addr = runtime_env.get("VAULT_ADDR", "").strip()
    token = runtime_env.get("VAULT_TOKEN", "").strip()
    if not addr or not token:
        return None

    mount = runtime_env.get("VAULT_MOUNT_POINT", "").strip().strip("/")
    config_path = runtime_env.get("VAULT_CONFIG_PATH", "").strip().strip("/")
    if config_path:
        mount = "/".join([part for part in (mount, config_path) if part])

    try:
        return VaultClient(
            VaultConnectionConfig(
                server=addr,
                token=token,
                timeout_seconds=10.0,
                mount_point=mount,
            )
        )
    except Exception:
        return None


def _resolve_env_value(raw_value: str) -> str:
    value = raw_value.strip()
    if not value:
        return value
    match = _VAULT_REF_PATTERN.match(value)
    if match is None:
        return value
    client = _vault_client()
    if client is None:
        return value
    resolved = resolve_vault_identifier(match.group(1), vault=client)
    if isinstance(resolved, (str, int, float, bool)):
        resolved_text = str(resolved).strip()
        if resolved_text:
            return resolved_text
    return value


def _load_env_file(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        if not key:
            continue
        # Explicit process values select runtime-specific test resources such as
        # the image built by docker-build.sh; an env file supplies only defaults.
        runtime_env.setdefault(key, _resolve_env_value(value.strip()))


def _consume_optional_test_env_keys() -> None:
    for key in _OPTIONAL_TEST_ENV_KEYS:
        runtime_env.get(key, "")


@pytest.fixture(scope="session", autouse=True)
def load_env_files(pytestconfig: pytest.Config) -> None:
    env_path = pytestconfig.getoption("--env")
    if not env_path:
        pytest.fail("ERROR: --env parameter REQUIRED (e.g. --env tests/env-UT)")
    path = Path(env_path)
    if not path.exists():
        pytest.fail(f"ERROR: env file not found: {path}")
    _load_env_file(path)
    _consume_optional_test_env_keys()


# --- PS-REQ-TEST-TRACE marker enforcement (added by rtt-2026-06-12 Instruction 3 uplift) ---
# See PS-REQ-TEST-TRACE v1.0 §6.2 — fails session if any test lacks tier + surface + req()/probe markers.

import sys

_PS_REQ_TIER_MARKERS = {"QT", "UT", "ST", "IT", "AT"}
_PS_REQ_SURFACE_MARKERS = {"api", "mcp", "a2a", "webui", "cli", "internal"}


def pytest_collection_modifyitems(config, items):
    """PS-REQ-TEST-TRACE marker enforcement."""
    failures = []
    for item in items:
        marker_names = {m.name for m in item.iter_markers()}
        is_probe = "probe" in marker_names
        if not (marker_names & _PS_REQ_TIER_MARKERS):
            failures.append(f"{item.nodeid}: missing @pytest.mark.<tier> per PS-REQ-TEST-TRACE §6")
        if not (marker_names & _PS_REQ_SURFACE_MARKERS):
            failures.append(f"{item.nodeid}: missing @pytest.mark.<surface> per PS-REQ-TEST-TRACE §6")
        if not is_probe:
            req_marker = item.get_closest_marker("req")
            if req_marker is None or not req_marker.args:
                failures.append(
                    f"{item.nodeid}: missing @pytest.mark.req('FR-NNN') per PS-REQ-TEST-TRACE §6 "
                    "(every test MUST bind a semantic requirement; the W28C-1711-R3 orphan exemption was retired in W28E-1802A)"
                )
    if failures:
        msg = "PS-REQ-TEST-TRACE marker enforcement failed for " + str(len(failures)) + " test(s):\n  " + "\n  ".join(failures[:20])
        if len(failures) > 20:
            msg += f"\n  ... and {len(failures) - 20} more"
        print(msg, file=sys.stderr)
        import pytest
        pytest.exit(msg, returncode=2)
