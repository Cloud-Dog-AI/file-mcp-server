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

"""Build helper images required by the project Dockerfile for IT docker tests.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Synthesizes local source images (cloud_dog_*_src) from installed
platform packages so Docker integration tests can build the project image.
Requirements: FR1.26
Tasks: W28A-516
Architecture: 4.1 Authentication, 5. Tool Interface
Tests: IT1.1, IT1.2
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import shutil
import tempfile
from typing import Callable


_IMAGE_SPECS: dict[str, dict[str, str]] = {
    "cloud_dog_site_packages": {
        "cloud_dog_api_kit": "cloud_dog_api_kit",
        "cloud_dog_idam": "cloud_dog_idam",
    },
    "cloud_dog_config_src": {"cloud_dog_config": "cloud_dog_config"},
    "cloud_dog_logging_src": {"cloud_dog_logging": "cloud_dog_logging"},
    "cloud_dog_db_src": {"cloud_dog_db": "cloud_dog_db"},
    "cloud_dog_jobs_src": {"cloud_dog_jobs": "cloud_dog_jobs"},
}


def _module_path(module_name: str) -> Path:
    module = import_module(module_name)
    module_file = getattr(module, "__file__", "")
    path = Path(module_file).resolve().parent if module_file else Path()
    if not path.exists():
        raise RuntimeError(f"Unable to resolve module path for {module_name}")
    return path


def ensure_cloud_dog_source_images(
    *,
    repo_root: Path,
    docker_cmd: Callable[..., list[str]],
    run_cmd: Callable[[list[str], Path, bool], object],
) -> None:
    """Ensure helper images required by Dockerfile multi-stage copies exist."""
    for image_name, modules in _IMAGE_SPECS.items():
        inspect_result = run_cmd(
            docker_cmd("image", "inspect", image_name), repo_root, False
        )
        if getattr(inspect_result, "returncode", 1) == 0:
            continue

        with tempfile.TemporaryDirectory(prefix=f"{image_name}-", dir=str(repo_root)) as td:
            context_dir = Path(td)
            dockerfile_lines = ["FROM scratch"]
            for module_name, folder_name in modules.items():
                source_dir = _module_path(module_name)
                target_dir = context_dir / folder_name
                shutil.copytree(source_dir, target_dir)
                dockerfile_lines.append(f"COPY {folder_name} /{folder_name}")
            (context_dir / "Dockerfile").write_text(
                "\n".join(dockerfile_lines) + "\n", encoding="utf-8"
            )
            run_cmd(
                docker_cmd("build", "-t", image_name, str(context_dir)),
                repo_root,
                True,
            )
