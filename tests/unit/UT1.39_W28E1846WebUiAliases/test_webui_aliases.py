from __future__ import annotations

import ast
from pathlib import Path

import pytest

from file_mcp_server.route_guards import _is_ui_path

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _static_method_return_literal(method_name: str) -> object:
    source = Path("src/file_mcp_server/server_runtime.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            for statement in node.body:
                if isinstance(statement, ast.Return):
                    return ast.literal_eval(statement.value)
    raise AssertionError(f"{method_name} return literal not found")


@pytest.mark.UT
@pytest.mark.webui
@pytest.mark.req("FR-022")
def test_profile_connection_aliases_route_to_storage_profiles() -> None:
    aliases = _static_method_return_literal("_canonical_ui_aliases")
    route_paths = _static_method_return_literal("_ui_route_paths")

    assert aliases["/profiles"] == "/storage-profiles"
    assert aliases["/source-connections"] == "/storage-profiles"
    assert "/profiles" in route_paths
    assert "/source-connections" in route_paths
    assert _is_ui_path("/profiles")
    assert _is_ui_path("/source-connections")
