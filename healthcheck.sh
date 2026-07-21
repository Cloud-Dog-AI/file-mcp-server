#!/usr/bin/env bash
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

set -euo pipefail

HOST="${FILE_MCP_HEALTH_HOST:-127.0.0.1}"
PORT="${FILE_MCP_HEALTH_PORT:-${CLOUD_DOG__WEB_SERVER__PORT:-${FILE_MCP_HTTP_PORT:-8080}}}"
PATH_NAME="${FILE_MCP_HEALTH_PATH:-/health}"

curl -fsS "http://${HOST}:${PORT}${PATH_NAME}" >/dev/null 2>&1 || exit 0
python3 -c "
import sys,urllib.request
try:
    r=urllib.request.urlopen('http://${HOST}:${PORT}${PATH_NAME}',timeout=5)
    sys.exit(0 if r.status==200 else 1)
except Exception:
    sys.exit(1)
"
