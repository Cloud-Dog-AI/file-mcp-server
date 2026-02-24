#!/usr/bin/env bash
# Verification script for file-mcp-server IDAM migration (4.2.d)
#
# Usage: bash verify-file-mcp-server-IDAM.sh
# Exit code 0 = ALL PASS, non-zero = FAILURE

set -uo pipefail

PROJECT="/opt/iac/Development/cloud-dog-ai/file-mcp-server"
VENV="$PROJECT/.venv/bin"
ENV_FILE="$PROJECT/tests/env-IT"
PYTHONPATH_VALUE="$PROJECT/src:."
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

echo "=== file-mcp-server IDAM Migration Verification ==="
echo ""

# Prerequisite checks
if bash "$PROJECT/migration/verify/verify-file-mcp-server-CONFIG.sh" >/tmp/verify-idam-config.log 2>&1; then
    check "PREREQ CONFIG verify" 0
else
    check "PREREQ CONFIG verify" 1
    cat /tmp/verify-idam-config.log
fi

if bash "$PROJECT/migration/verify/verify-file-mcp-server-LOGGING.sh" >/tmp/verify-idam-logging.log 2>&1; then
    check "PREREQ LOGGING verify" 0
else
    check "PREREQ LOGGING verify" 1
    cat /tmp/verify-idam-logging.log
fi

if bash "$PROJECT/migration/verify/verify-file-mcp-server-API-KIT.sh" >/tmp/verify-idam-api-kit.log 2>&1; then
    check "PREREQ API-KIT verify" 0
else
    check "PREREQ API-KIT verify" 1
    cat /tmp/verify-idam-api-kit.log
fi

# Universal gates
run_cmd "QG-1 ruff check src/" "$VENV/ruff" check "$PROJECT/src/"
run_cmd "QG-2 ruff format --check src/" "$VENV/ruff" format --check "$PROJECT/src/"
run_cmd "QG-3 mypy src/" env PYTHONPATH="$PYTHONPATH_VALUE" "$VENV/mypy" "$PROJECT/src/"

if env PYTHONPATH="$PYTHONPATH_VALUE" "$VENV/pytest" \
    "$(test_path test_auth.py)" \
    "$(test_path test_scope_policy.py)" \
    -v --env "$ENV_FILE" >/tmp/verify-idam-smoke.log 2>&1; then
    check "QG-7 Smoke tests" 0
else
    check "QG-7 Smoke tests" 1
    tail -n 200 /tmp/verify-idam-smoke.log
fi

if env PYTHONPATH="$PYTHONPATH_VALUE" "$VENV/pytest" \
    "$(test_path test_auth.py)" \
    "$(test_path test_scope_policy.py)" \
    "$(test_path test_system_auth_health.py)" \
    "$(test_path test_integration_multi_profile_routing_http.py)" \
    "$(test_path test_integration_config_matrix_harness_http.py)" \
    "$(test_path test_integration_scoped_ops.py)" \
    "$(test_path test_application_security_boundary.py)" \
    "$(test_path test_application_preprod_profile_chain_http.py)" \
    -v --env "$ENV_FILE" >/tmp/verify-idam-regression.log 2>&1; then
    check "QG-8 Regression tests" 0
else
    check "QG-8 Regression tests" 1
    tail -n 240 /tmp/verify-idam-regression.log
fi

if grep -Rsn "cloud_dog_idam" "$PROJECT/src/" --include="*.py" >/tmp/verify-idam-imports.log 2>&1; then
    check "QG-9 cloud_dog_idam imported" 0
else
    check "QG-9 cloud_dog_idam imported" 1
fi

LEGACY_IMPORTS=$(grep -Rsn "from file_mcp_server.auth import" "$PROJECT/src/" --include="*.py" 2>/dev/null | wc -l)
check "QG-10 no runtime imports from file_mcp_server.auth" "$LEGACY_IMPORTS"

# IDAM-specific gates
FILE_TOOLS_AUTH=$(grep -Rsn "def.*authenticate\|def.*check_auth\|verify_token" "$PROJECT/src/file_tools/" --include="*.py" 2>/dev/null | wc -l)
check "QG-I1 no bespoke auth in file_tools library code" "$FILE_TOOLS_AUTH"

if env PYTHONPATH="$PYTHONPATH_VALUE" "$VENV/pytest" \
    "$(test_path test_system_auth_health.py)::test_auth_enforcement_and_health" \
    -v --env "$ENV_FILE" >/tmp/verify-idam-i2.log 2>&1; then
    check "QG-I2 unauthenticated protected request rejected" 0
else
    check "QG-I2 unauthenticated protected request rejected" 1
    tail -n 120 /tmp/verify-idam-i2.log
fi

if env PYTHONPATH="$PYTHONPATH_VALUE" "$VENV/pytest" \
    "$(test_path test_integration_multi_profile_routing_http.py)::test_multi_profile_selection_auth_and_scope_controls" \
    -v --env "$ENV_FILE" >/tmp/verify-idam-i3.log 2>&1; then
    check "QG-I3 low-privilege out-of-scope profile access rejected" 0
else
    check "QG-I3 low-privilege out-of-scope profile access rejected" 1
    tail -n 120 /tmp/verify-idam-i3.log
fi

QUERY_TOKEN_HITS=$(grep -Rsn "query_params.*token\|query.*admin_token" "$PROJECT/src/" --include="*.py" 2>/dev/null | wc -l)
check "QG-I4 query-string token/admin token paths removed" "$QUERY_TOKEN_HITS"

if env PYTHONPATH="$PYTHONPATH_VALUE" "$VENV/python" - <<'PY' >/tmp/verify-idam-i5.log 2>&1
import asyncio
from cloud_dog_idam.audit.emitter import AuditEmitter
from file_mcp_server.idam_adapter import ApiKeyTokenVerifier

audit = AuditEmitter(also_log_to_memory=True)
verifier = ApiKeyTokenVerifier(["secret"], audit_emitter=audit)
token = asyncio.run(verifier.verify_token("secret"))
assert token is not None
events = audit.list()
assert events, "expected auth audit events"
details_text = " ".join(str(event.details) for event in events)
assert "secret" not in details_text.lower(), "raw API key leaked in audit details"
assert "sha256:" in details_text, "fingerprint missing from audit details"
PY
then
    check "QG-I5 auth audit uses fingerprints only (no raw API key)" 0
else
    check "QG-I5 auth audit uses fingerprints only (no raw API key)" 1
    cat /tmp/verify-idam-i5.log
fi

echo ""
echo "=== RESULTS: ${PASS} passed, ${FAIL} failed ==="
echo ""
if [ "$FAIL" -eq 0 ]; then
    echo "VERDICT: ALL PASS — file-mcp-server IDAM migration is COMPLETE."
    exit 0
else
    echo "VERDICT: ${FAIL} GATE(S) FAILED — review failures above."
    exit 1
fi
