#!/usr/bin/env bash
# Verification script for file-mcp-server LOGGING migration (4.2.b)
#
# Usage: bash verify-file-mcp-server-LOGGING.sh
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

echo "=== file-mcp-server LOGGING Migration Verification ==="
echo ""

# Prerequisite check (CONFIG migration complete)
if bash "$PROJECT/migration/verify/verify-file-mcp-server-CONFIG.sh" >/tmp/verify-config.log 2>&1; then
    check "PREREQ CONFIG verify" 0
else
    check "PREREQ CONFIG verify" 1
    cat /tmp/verify-config.log
fi

# QG-1/2/3
run_cmd "QG-1 ruff check src/" "$VENV/ruff" check "$PROJECT/src/"
run_cmd "QG-2 ruff format --check src/" "$VENV/ruff" format --check "$PROJECT/src/"
run_cmd "QG-3 mypy src/" "$VENV/mypy" "$PROJECT/src/"

# QG-4
COUNT=$(grep -rn "os\.environ\|os\.getenv" "$PROJECT/src/file_tools/audit/" "$PROJECT/src/file_tools/observability.py" --include="*.py" 2>/dev/null | wc -l)
check "QG-4 No env reads in logging modules" "$COUNT"

# QG-7 smoke
if PYTHONPATH="$PROJECT/src:." "$VENV/pytest" \
    "$PROJECT/tests/test_audit.py" \
    "$PROJECT/tests/test_observability.py" \
    -v --env "$PROJECT/private/env-accept-smoke" >/tmp/verify-logging-smoke.log 2>&1; then
    check "QG-7 Smoke tests" 0
else
    check "QG-7 Smoke tests" 1
    tail -n 80 /tmp/verify-logging-smoke.log
fi

# QG-8 regression
if PYTHONPATH="$PROJECT/src:." "$VENV/pytest" \
    "$PROJECT/tests/test_audit.py" \
    "$PROJECT/tests/test_observability.py" \
    "$PROJECT/tests/test_system_audit_integrity.py" \
    "$PROJECT/tests/test_system_snapshot_retention.py" \
    "$PROJECT/tests/test_integration_structured_audit_snapshot.py" \
    "$PROJECT/tests/test_application_search_edit_audit_workflow.py" \
    -v --env "$PROJECT/private/env-accept-smoke" >/tmp/verify-logging-regression.log 2>&1; then
    check "QG-8 Regression tests" 0
else
    check "QG-8 Regression tests" 1
    tail -n 120 /tmp/verify-logging-regression.log
fi

# QG-9
if grep -r "cloud_dog_logging" "$PROJECT/src/" --include="*.py" >/tmp/verify-logging-imports.log 2>&1; then
    check "QG-9 cloud_dog_logging imports present" 0
else
    check "QG-9 cloud_dog_logging imports present" 1
fi

# QG-10
COUNT=$(grep -r "from file_tools.audit.logger import\|from file_tools.observability import" "$PROJECT/src/" --include="*.py" 2>/dev/null | wc -l)
check "QG-10 no legacy imports in non-adapter code" "$COUNT"

# QG-L1/L2/L5 (grep gates)
COUNT=$(grep -Rsn "print(" "$PROJECT/src/file_tools/" "$PROJECT/src/file_mcp_server/" --include="*.py" 2>/dev/null | wc -l)
check "QG-L1 no print() in server/file_tools" "$COUNT"

COUNT=$(grep -Rsn "logging\.getLogger\|logging\.basicConfig" "$PROJECT/src/file_tools/" --include="*.py" 2>/dev/null | wc -l)
check "QG-L2 no stdlib logger bootstrap in file_tools" "$COUNT"

COUNT=$(grep -Rsn "json\.dumps.*logger\|logger.*json\.dumps" "$PROJECT/src/" --include="*.py" 2>/dev/null | wc -l)
check "QG-L5 no manual JSON serialisation logging" "$COUNT"

# QG-L3/L4/L6 (runtime probes without network sockets)
if PYTHONPATH="$PROJECT/src:." "$VENV/python" - <<'PY' >/tmp/verify-logging-runtime.log 2>&1
from __future__ import annotations
import json
import tempfile
from pathlib import Path

from cloud_dog_logging.correlation import set_correlation_id, clear_correlation_id

from file_tools.audit.adapter import AuditLogger, build_event
from file_tools.config.models import AuditConfig, ObservabilityConfig, ProfileConfig
from file_tools.observability import configure_operational_logger

# QG-L3: audit JSONL validity + required fields
with tempfile.TemporaryDirectory(prefix="verify-qgl3-") as tmp:
    base = Path(tmp)
    audit_path = base / "audit.jsonl"
    logger = AuditLogger(audit_path)
    set_correlation_id("verify-correlation")
    logger.write(
        build_event(
            tool="read_file",
            action="tool_call",
            status="ok",
            outcome="success",
            profile="default",
            params={"path": "/tmp/a.txt"},
            paths={"path": "/tmp/a.txt"},
            details={"note": "runtime"},
        )
    )
    clear_correlation_id()
    rows = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows, "no audit rows"
    required = {"timestamp", "event_type", "actor", "action", "outcome", "correlation_id", "service", "target", "details"}
    assert not [r for r in rows if required - set(r.keys())], "missing required audit fields"

# QG-L4 and QG-L6 via app logger output
with tempfile.TemporaryDirectory(prefix="verify-qgl46-") as tmp:
    base = Path(tmp)
    server_log = base / "server.log"
    profile = ProfileConfig(
        auth={"api_keys": ["secret-key"]},
        scope={"roots": ["/"]},
        observability=ObservabilityConfig(enabled=True, log_path=str(server_log), level="INFO"),
        audit=AuditConfig(log_path=str(base / "audit.log.jsonl")),
    )
    app = configure_operational_logger(profile)
    set_correlation_id("verify-correlation")
    app.info(
        "tool_call",
        event="tool_call",
        tool="read_file",
        token="sensitive-token",
        password="sensitive-password",
        nested={"secret": "sensitive-secret", "api_key": "sensitive-api-key"},
    )
    clear_correlation_id()
    content = server_log.read_text(encoding="utf-8")
    row = json.loads(content.splitlines()[-1])
    assert row.get("correlation_id"), "missing correlation_id"
    assert "sensitive-token" not in content
    assert "sensitive-password" not in content
    assert "sensitive-secret" not in content
    assert "sensitive-api-key" not in content
    assert "***REDACTED***" in content
PY
then
    check "QG-L3 audit JSONL valid + required fields" 0
    check "QG-L4 correlation_id present in request-style entry" 0
    check "QG-L6 redaction of token/secret/password/api_key" 0
else
    check "QG-L3 audit JSONL valid + required fields" 1
    check "QG-L4 correlation_id present in request-style entry" 1
    check "QG-L6 redaction of token/secret/password/api_key" 1
    cat /tmp/verify-logging-runtime.log
fi

echo ""
echo "=== RESULTS: ${PASS} passed, ${FAIL} failed ==="
echo ""
if [ "$FAIL" -eq 0 ]; then
    echo "VERDICT: ALL PASS — file-mcp-server LOGGING migration is COMPLETE."
    exit 0
else
    echo "VERDICT: ${FAIL} GATE(S) FAILED — review failures above."
    exit 1
fi
