"""Server transport/dispatch scaffolding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, TextIO

import json
import sys

from file_tools.tools import ToolRegistry


@dataclass(frozen=True)
class JsonRpcError:
    code: int
    message: str


def _build_response(request_id: Any, result: Any = None, error: JsonRpcError | None = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error:
        payload["error"] = {"code": error.code, "message": error.message}
    else:
        payload["result"] = result
    return payload


class DispatchError(RuntimeError):
    """Raised when a request cannot be dispatched."""


class StdioServer:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def handle_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        request_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params") or {}

        if not method:
            return _build_response(request_id, error=JsonRpcError(-32600, "Missing method"))

        try:
            if method == "tools/list":
                tools = [
                    {
                        "name": tool.meta.name,
                        "description": tool.meta.description,
                        "mutating": tool.meta.mutating,
                        "requires_validation": tool.meta.requires_validation,
                        "supports_dry_run": tool.meta.supports_dry_run,
                    }
                    for tool in self.registry.list_tools()
                ]
                return _build_response(request_id, result=tools)
            if method == "tools/call":
                name = params.get("name")
                arguments = params.get("arguments") or {}
                if not name:
                    raise DispatchError("Missing tool name")
                tool = self.registry.get(name)
                result = tool.handler(**arguments)
                return _build_response(request_id, result=result)
            raise DispatchError(f"Unknown method: {method}")
        except DispatchError as exc:
            return _build_response(request_id, error=JsonRpcError(-32601, str(exc)))
        except Exception as exc:  # pragma: no cover - defensive
            return _build_response(request_id, error=JsonRpcError(-32000, str(exc)))

    def serve(self, *, input_stream: Optional[TextIO] = None, output_stream: Optional[TextIO] = None) -> None:
        in_stream = input_stream or sys.stdin
        out_stream = output_stream or sys.stdout
        for line in in_stream:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                response = _build_response(None, error=JsonRpcError(-32700, str(exc)))
            else:
                response = self.handle_request(payload)
            out_stream.write(json.dumps(response) + "\n")
            out_stream.flush()
