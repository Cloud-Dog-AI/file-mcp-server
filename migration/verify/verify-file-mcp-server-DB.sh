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

# Verification script for file-mcp-server DB migration (cloud_dog_db).
# Exit code 0 = all gates pass. Non-zero = one or more gates failed.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$SCRIPT_DIR/../.." && pwd)"
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

echo "=== file-mcp-server DB Migration Verification ==="
echo ""

if grep -q '"cloud_dog_db>=' "$PROJECT/pyproject.toml" 2>/dev/null; then
    check "QG-DB-1 cloud_dog_db declared in pyproject" 0
else
    check "QG-DB-1 cloud_dog_db declared in pyproject" 1
fi

if grep -q "from cloud_dog_db import" "$PROJECT/src/file_mcp_server/db/runtime.py" 2>/dev/null; then
    check "QG-DB-2 runtime imports cloud_dog_db" 0
else
    check "QG-DB-2 runtime imports cloud_dog_db" 1
fi

if grep -q "probe_database" "$PROJECT/src/file_mcp_server/db/runtime.py" 2>/dev/null; then
    check "QG-DB-3 runtime uses probe_database" 0
else
    check "QG-DB-3 runtime uses probe_database" 1
fi

if [ -d "$PROJECT/database/migrations/cloud_dog_db" ] && [ -d "$PROJECT/database/migrations/cloud_dog_db/versions" ]; then
    check "QG-DB-4 cloud_dog_db migration tree present" 0
else
    check "QG-DB-4 cloud_dog_db migration tree present" 1
fi

COUNT=$(find "$PROJECT/database/migrations/cloud_dog_db/versions" -type f -name '*.py' 2>/dev/null | wc -l)
if [ "$COUNT" -ge 1 ]; then
    check "QG-DB-5 migration versions present (count=${COUNT})" 0
else
    check "QG-DB-5 migration versions present (count=${COUNT})" 1
fi

COUNT=$(grep -RInE "create_engine\(|sessionmaker\(|sqlite3\.connect" "$PROJECT/src" --include='*.py' 2>/dev/null | wc -l)
check "QG-DB-6 no direct engine/session/sqlite bypass in src (count=${COUNT})" "$COUNT"

if grep -q "R-DB-01" "$PROJECT/REQUIREMENTS.md" 2>/dev/null && grep -q "UT-DB-01" "$PROJECT/TESTS.md" 2>/dev/null; then
    check "QG-DB-7 DB requirements/tests traceability anchors present" 0
else
    check "QG-DB-7 DB requirements/tests traceability anchors present" 1
fi

echo ""
echo "=== RESULTS: ${PASS} passed, ${FAIL} failed ==="
echo ""
if [ "$FAIL" -eq 0 ]; then
    echo "VERDICT: ALL PASS — file-mcp-server DB migration verifier checks are green."
    exit 0
else
    echo "VERDICT: ${FAIL} gate(s) failed — review failures above."
    exit 1
fi
