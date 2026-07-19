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

"""Build and resolve the configured Docker image used by integration tests."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests.env_runtime import env_get


def require_dev_docker_test_image(repo_root: Path, docker_cmd: list[str]) -> str:
    """Return the configured IT image, building it through the sanctioned dev path."""
    image = env_get("FILE_MCP_DOCKER_TEST_IMAGE", "").strip()
    if not image:
        pytest.fail("FILE_MCP_DOCKER_TEST_IMAGE is required for Docker integration tests")

    inspect = subprocess.run(
        [*docker_cmd, "image", "inspect", image],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if inspect.returncode == 0:
        return image

    if env_get("FILE_MCP_DOCKER_BUILD_VARIANT", "").strip() != "dev":
        pytest.fail("FILE_MCP_DOCKER_BUILD_VARIANT must be dev for Docker integration tests")

    pypi_url = env_get("FILE_MCP_DOCKER_PYPI_URL", "").strip()
    pypi_username = env_get("FILE_MCP_DOCKER_PYPI_USERNAME", "").strip()
    pypi_password = env_get("FILE_MCP_DOCKER_PYPI_PASSWORD", "").strip()
    if not all((pypi_url, pypi_username, pypi_password)):
        pytest.fail("Docker IT dev build requires Vault-backed FILE_MCP_DOCKER_PYPI_* settings")

    tag = image.rsplit(":", 1)[-1] if ":" in image else "latest"
    build_env = os.environ.copy()
    build_env.update(
        {
            "PYPI_URL": pypi_url,
            "PYPI_USERNAME": pypi_username,
            "PYPI_PASSWORD": pypi_password,
        }
    )
    result = subprocess.run(
        ["./docker-build.sh", tag, "--variant", "dev"],
        cwd=repo_root,
        env=build_env,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"docker-build.sh {tag} --variant dev failed with exit {result.returncode}")

    verified = subprocess.run(
        [*docker_cmd, "image", "inspect", image],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if verified.returncode != 0:
        pytest.fail(f"docker-build.sh succeeded but did not produce {image}")
    return image
