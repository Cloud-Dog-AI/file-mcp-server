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

# Verification script for file-mcp-server API-KIT migration (4.2.c)
#
# Usage: bash verify-file-mcp-server-API-KIT.sh
# Exit code 0 = ALL PASS, non-zero = FAILURE

set -uo pipefail

PROJECT="/opt/iac/Development/cloud-dog-ai/file-mcp-server"
VENV="$PROJECT/.venv/bin"
FAIL=0
PASS=0

check() {
    local gate="$1"
    local result="$2"
    if [ "$result" -eq 0 ]; then
        echo "  PASS  $gate"
        PASS=$((PASS + 1))
    else
        echo "  FAIL  $gate"
        FAIL=$((FAIL + 1))
    fi
}

run_cmd() {
    local gate="$1"
    shift
    if "$@"; then
        check "$gate" 0
    else
        check "$gate" 1
    fi
}

test_path() {
    local test_name="$1"
    local found
    found=$(find "$PROJECT/tests" -type f -name "$test_name" | head -n 1)
    if [ -z "$found" ]; then
        echo "Missing test file: $test_name" >&2
        return 1
    fi
    echo "$found"
}

echo "=== file-mcp-server API-KIT Migration Verification ==="
echo ""

# Prerequisite checks
if bash "$PROJECT/migration/verify/verify-file-mcp-server-CONFIG.sh" >/tmp/verify-api-config.log 2>&1; then
    check "PREREQ CONFIG verify" 0
else
    check "PREREQ CONFIG verify" 1
    cat /tmp/verify-api-config.log
fi

if bash "$PROJECT/migration/verify/verify-file-mcp-server-LOGGING.sh" >/tmp/verify-api-logging.log 2>&1; then
    check "PREREQ LOGGING verify" 0
else
    check "PREREQ LOGGING verify" 1
    cat /tmp/verify-api-logging.log
fi

# Universal gates
run_cmd "QG-1 ruff check src/" "$VENV/ruff" check "$PROJECT/src/"
run_cmd "QG-2 ruff format --check src/" "$VENV/ruff" format --check "$PROJECT/src/"
run_cmd "QG-3 mypy src/" "$VENV/mypy" "$PROJECT/src/"

if PYTHONPATH="$PROJECT/src:." "$VENV/pytest" \
    "$(test_path test_server_dispatch.py)" \
    "$(test_path test_server_runtime.py)" \
    "$(test_path test_endpoint_health.py)" \
    "$(test_path test_api_kit_contract.py)" \
    -v --env "$PROJECT/tests/env-IT" >/tmp/verify-api-smoke.log 2>&1; then
    check "QG-7 Smoke tests" 0
else
    check "QG-7 Smoke tests" 1
    tail -n 120 /tmp/verify-api-smoke.log
fi

REGRESSION_TESTS=(
    "$(test_path test_server_dispatch.py)"
    "$(test_path test_server_runtime.py)"
    "$(test_path test_endpoint_health.py)"
    "$(test_path test_lifecycle.py)"
    "$(test_path test_system_auth_health.py)"
    "$(test_path test_system_endpoint_restart_threshold.py)"
    "$(test_path test_system_error_contract.py)"
    "$(test_path test_server_http_integration.py)"
    "$(test_path test_integration_multi_profile_routing_http.py)"
    "$(test_path test_application_lifecycle_workflow.py)"
)
if [ "${FILE_MCP_RUN_PREPROD_AT:-0}" = "1" ]; then
    REGRESSION_TESTS+=("$(test_path test_application_preprod_profile_chain_http.py)")
fi

if PYTHONPATH="$PROJECT/src:." "$VENV/pytest" \
    "${REGRESSION_TESTS[@]}" \
    -v --env "$PROJECT/tests/env-IT" >/tmp/verify-api-regression.log 2>&1; then
    check "QG-8 Regression tests" 0
else
    check "QG-8 Regression tests" 1
    tail -n 200 /tmp/verify-api-regression.log
fi

if grep -Rsn "cloud_dog_api_kit" "$PROJECT/src/" --include="*.py" >/tmp/verify-api-imports.log 2>&1; then
    check "QG-9 cloud_dog_api_kit imported" 0
else
    check "QG-9 cloud_dog_api_kit imported" 1
fi

# API-kit specific gates
FASTAPI_USE=$(grep -Rsn "FastAPI(" "$PROJECT/src/file_mcp_server/" --include="*.py" 2>/dev/null || true)
if [ -z "$FASTAPI_USE" ]; then
    check "QG-A3 FastAPI() usage controlled (no direct instantiation)" 0
else
    NON_KIT=$(printf "%s\n" "$FASTAPI_USE" | grep -v "cloud_dog_api_kit" || true)
    if [ -z "$NON_KIT" ]; then
        check "QG-A3 FastAPI() only via API-kit pathways" 0
    else
        check "QG-A3 FastAPI() only via API-kit pathways" 1
        echo "$NON_KIT"
    fi
fi

LINES=$(wc -l < "$PROJECT/src/file_mcp_server/server.py" 2>/dev/null || echo 9999)
if [ "$LINES" -lt 200 ]; then
    check "QG-A6 server.py decomposed (${LINES} lines)" 0
else
    check "QG-A6 server.py decomposed (${LINES} lines, need <200)" 1
fi

COUNT=$(grep -Rsn "request.query_params.*token\|query.*admin_token" "$PROJECT/src/" --include="*.py" 2>/dev/null | wc -l)
check "QG-A7 query-string admin token path removed" "$COUNT"

# Runtime endpoint checks (A1/A2/A4/A5)
TMP_ENV=$(mktemp)
PIDFILE="$PROJECT/.run/verify-api-kit.pid"
cleanup() {
    "$PROJECT/server_control.sh" --env "$TMP_ENV" --pidfile "$PIDFILE" stop >/dev/null 2>&1 || true
    rm -f "$TMP_ENV"
}
trap cleanup EXIT

cp "$PROJECT/tests/env-IT" "$TMP_ENV"
echo "FILE_MCP_ADMIN_UI_ENABLED=false" >> "$TMP_ENV"
echo "FILE_MCP_ADMIN_UI_TOKEN=" >> "$TMP_ENV"

if "$PROJECT/server_control.sh" --env "$TMP_ENV" --pidfile "$PIDFILE" start >/tmp/verify-api-start.log 2>&1; then
    START_OK=0
else
    START_OK=1
    cat /tmp/verify-api-start.log
fi
check "Runtime server start" "$START_OK"

PORT=$(grep '^FILE_MCP_HTTP_PORT=' "$TMP_ENV" | head -1 | cut -d= -f2)
if [ -z "$PORT" ]; then
    PORT="18090"
fi

HEALTH_OK=1
for _ in $(seq 1 60); do
    if curl -fsS "http://127.0.0.1:${PORT}/health" >/tmp/verify-api-health.json 2>/dev/null; then
        HEALTH_OK=0
        break
    fi
    sleep 1
done
check "Runtime health responds" "$HEALTH_OK"

if [ "$HEALTH_OK" -eq 0 ]; then
    if "$VENV/python" - <<'PY' >/tmp/verify-a1.out 2>&1
import json
from pathlib import Path
payload = json.loads(Path("/tmp/verify-api-health.json").read_text(encoding="utf-8"))
assert "status" in payload
assert "checks" in payload
assert "version" in payload
PY
    then
        check "QG-A1 /health returns status+checks+version" 0
    else
        check "QG-A1 /health returns status+checks+version" 1
        cat /tmp/verify-a1.out
    fi

    if curl -fsS "http://127.0.0.1:${PORT}/ready" >/tmp/verify-api-ready.json 2>/dev/null; then
        if "$VENV/python" - <<'PY' >/tmp/verify-a4.out 2>&1
import json
from pathlib import Path
payload = json.loads(Path("/tmp/verify-api-ready.json").read_text(encoding="utf-8"))
assert "status" in payload
PY
        then
            check "QG-A4 /ready returns readiness status" 0
        else
            check "QG-A4 /ready returns readiness status" 1
            cat /tmp/verify-a4.out
        fi
    else
        check "QG-A4 /ready returns readiness status" 1
    fi

    if curl -fsS "http://127.0.0.1:${PORT}/live" >/tmp/verify-api-live.json 2>/dev/null; then
        if "$VENV/python" - <<'PY' >/tmp/verify-a5.out 2>&1
import json
from pathlib import Path
payload = json.loads(Path("/tmp/verify-api-live.json").read_text(encoding="utf-8"))
assert payload.get("status") == "ok"
PY
        then
            check "QG-A5 /live returns liveness status" 0
        else
            check "QG-A5 /live returns liveness status" 1
            cat /tmp/verify-a5.out
        fi
    else
        check "QG-A5 /live returns liveness status" 1
    fi

    CODE=$(curl -sS -o /tmp/verify-api-err.json -w "%{http_code}" -X POST "http://127.0.0.1:${PORT}/admin/reload")
    if [ "$CODE" -ge 400 ] && [ "$CODE" -lt 500 ]; then
        if "$VENV/python" - <<'PY' >/tmp/verify-a2.out 2>&1
import json
from pathlib import Path
payload = json.loads(Path("/tmp/verify-api-err.json").read_text(encoding="utf-8"))
assert payload.get("ok") is False
errors = payload.get("errors")
assert isinstance(errors, list) and errors
assert "code" in errors[0] and "message" in errors[0]
meta = payload.get("meta") or {}
assert bool(meta.get("correlation_id"))
PY
        then
            check "QG-A2 4xx error envelope shape" 0
        else
            check "QG-A2 4xx error envelope shape" 1
            cat /tmp/verify-a2.out
        fi
    else
        check "QG-A2 4xx error envelope shape" 1
    fi
else
    check "QG-A1 /health returns status+checks+version" 1
    check "QG-A4 /ready returns readiness status" 1
    check "QG-A5 /live returns liveness status" 1
    check "QG-A2 4xx error envelope shape" 1
fi

echo ""
echo "=== RESULTS: ${PASS} passed, ${FAIL} failed ==="
echo ""
if [ "$FAIL" -eq 0 ]; then
    echo "VERDICT: ALL PASS — file-mcp-server API-KIT migration is COMPLETE."
    exit 0
else
    echo "VERDICT: ${FAIL} GATE(S) FAILED — review failures above."
    exit 1
fi
