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

# Verification script for file-mcp-server CONFIG migration (4.2.a)
# Run this script to get a single PASS/FAIL verdict.
# If ALL gates pass, the migration is COMPLETE. Do NOT re-execute the instruction.
#
# Usage: bash verify-file-mcp-server-CONFIG.sh
# Exit code 0 = ALL PASS, non-zero = FAILURE (details printed)

set -uo pipefail

PROJECT="/opt/iac/Development/cloud-dog-ai/file-mcp-server"
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

echo "=== file-mcp-server CONFIG Migration Verification ==="
echo ""

# QG-4: No os.environ/os.getenv in library code
COUNT=$(grep -rn "os\.environ\|os\.getenv\|import hvac\|overlay_secrets" "$PROJECT/src/file_tools/" --include="*.py" 2>/dev/null | wc -l)
check "QG-4  No os.environ in library code" "$COUNT"

# QG-C1: Same as QG-4 (belt and braces)
COUNT=$(grep -rn "os\.environ\|os\.getenv" "$PROJECT/src/file_tools/" --include="*.py" 2>/dev/null | wc -l)
check "QG-C1 No env reads in library" "$COUNT"

# QG-C8: No private API access
COUNT=$(grep -rn "_select_relevant_os_environ\|sys\.path\.insert" "$PROJECT/src/" --include="*.py" 2>/dev/null | wc -l)
check "QG-C8 No private API / sys.path hacks" "$COUNT"

# QG-9: cloud_dog_config imported
COUNT=$(grep -c "cloud_dog_config" "$PROJECT/src/file_tools/config/adapter.py" 2>/dev/null)
if [ "$COUNT" -ge 1 ]; then check "QG-9  cloud_dog_config imported" 0; else check "QG-9  cloud_dog_config imported" 1; fi

# QG-C3: Vault expressions in YAML (expect >= 8 each)
D_COUNT=$(grep -c "vault\.dev\.storage\." "$PROJECT/defaults.yaml" 2>/dev/null || echo 0)
C_COUNT=$(grep -c "vault\.dev\.storage\." "$PROJECT/config.yaml" 2>/dev/null || echo 0)
TOTAL=$((D_COUNT + C_COUNT))
if [ "$TOTAL" -ge 16 ]; then check "QG-C3 Vault expressions (${TOTAL} hits)" 0; else check "QG-C3 Vault expressions (${TOTAL} hits, need >=16)" 1; fi

# QG-C7: Correct S3 key naming
COUNT=$(grep -c "access_key_id" "$PROJECT/defaults.yaml" "$PROJECT/config.yaml" 2>/dev/null | tail -1 | grep -o '[0-9]*' || echo 0)
D_HIT=$(grep -c "access_key_id" "$PROJECT/defaults.yaml" 2>/dev/null || echo 0)
C_HIT=$(grep -c "access_key_id" "$PROJECT/config.yaml" 2>/dev/null || echo 0)
TOTAL=$((D_HIT + C_HIT))
if [ "$TOTAL" -ge 2 ]; then check "QG-C7 S3 key naming correct (${TOTAL} hits)" 0; else check "QG-C7 S3 key naming correct (${TOTAL} hits, need >=2)" 1; fi

# Adapter line count (target: <= 100)
LINES=$(wc -l < "$PROJECT/src/file_tools/config/adapter.py" 2>/dev/null || echo 999)
if [ "$LINES" -le 100 ]; then check "Adapter size (${LINES} lines, max 100)" 0; else check "Adapter size (${LINES} lines, max 100)" 1; fi

# Adapter uses public API only (load_config import)
if grep -q "from cloud_dog_config import load_config" "$PROJECT/src/file_tools/config/adapter.py" 2>/dev/null; then
    check "Adapter uses public API" 0
else
    check "Adapter uses public API" 1
fi

# No workaround patterns
COUNT=$(grep -rn "compat\|legacy.*layer\|override.*env\|workaround" "$PROJECT/src/file_tools/config/adapter.py" 2>/dev/null | wc -l)
check "No workaround patterns in adapter" "$COUNT"

# Loader shim is minimal
LINES=$(wc -l < "$PROJECT/src/file_tools/config/loader.py" 2>/dev/null || echo 999)
if [ "$LINES" -le 25 ]; then check "Loader shim size (${LINES} lines, max 25)" 0; else check "Loader shim size (${LINES} lines, max 25)" 1; fi

# No wrong S3 key names remaining
WRONG=$(grep -rn "vault\.dev\.storage\.s3\.access_key[^_]" "$PROJECT/defaults.yaml" "$PROJECT/config.yaml" 2>/dev/null | wc -l)
check "No wrong S3 key names (access_key without _id)" "$WRONG"

# No vault.dev.keys.api_key (doesn't exist in Vault)
WRONG=$(grep -rn "vault\.dev\.keys\.api_key" "$PROJECT/config.yaml" "$PROJECT/defaults.yaml" 2>/dev/null | wc -l)
check "No non-existent vault.dev.keys.api_key reference" "$WRONG"

# QG-C9: Env expression source audit (RULE 11 — drift prevention)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_AUDIT_SCRIPT="$SCRIPT_DIR/verify-env-expression-sources.sh"
if [ ! -x "$ENV_AUDIT_SCRIPT" ]; then
    ENV_AUDIT_SCRIPT="/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-platform-standards/migration/verify/verify-env-expression-sources.sh"
fi

if [ ! -x "$ENV_AUDIT_SCRIPT" ]; then
    check "QG-C9 Env expression source audit (audit script missing)" 1
else
    ENV_AUDIT_FAILS=$(bash "$ENV_AUDIT_SCRIPT" "$PROJECT" 2>&1 | grep -c "^  FAIL" || true)
    ENV_AUDIT_FAILS=${ENV_AUDIT_FAILS:-0}
    check "QG-C9 Env expression source audit (${ENV_AUDIT_FAILS} orphaned)" "$ENV_AUDIT_FAILS"
fi

# private/env-remote-storage uses Vault expressions
if [ -f "$PROJECT/private/env-remote-storage" ]; then
    VAULT_EXPRS=$(grep -c 'vault\.dev\.' "$PROJECT/private/env-remote-storage" 2>/dev/null || echo 0)
    if [ "$VAULT_EXPRS" -ge 4 ]; then check "env-remote-storage has Vault expressions (${VAULT_EXPRS})" 0; else check "env-remote-storage has Vault expressions (${VAULT_EXPRS}, need >=4)" 1; fi
else
    check "env-remote-storage exists" 1
fi

echo ""
echo "=== RESULTS: ${PASS} passed, ${FAIL} failed ==="
echo ""
if [ "$FAIL" -eq 0 ]; then
    echo "VERDICT: ALL PASS — file-mcp-server CONFIG migration is COMPLETE."
    echo ""
    echo "DO NOT re-execute the CONFIG instruction."
    echo "DO NOT re-audit env files."
    echo "DO NOT add workarounds."
    echo "Proceed to LOGGING migration (4.2.b)."
    exit 0
else
    echo "VERDICT: ${FAIL} GATE(S) FAILED — review failures above."
    exit 1
fi
