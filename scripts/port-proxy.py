#!/usr/bin/env python3
# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Description: Lightweight HTTP proxy for file-mcp-server standard port compatibility.
#   Forwards requests on API (8083) and MCP (8081) ports to the unified server (8080).

import http.server
import os
import sys
import threading
import urllib.request

MAIN_PORT = int(os.environ.get("CLOUD_DOG__WEB_SERVER__PORT", "8080"))
API_PORT = int(os.environ.get("CLOUD_DOG__API_SERVER__PORT", "8083"))
MCP_PORT = int(os.environ.get("CLOUD_DOG__MCP_SERVER__PORT", "8081"))


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    """Forward requests to the main unified server."""

    def do_GET(self):
        self._proxy()

    def do_POST(self):
        self._proxy()

    def _proxy(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else None
            req = urllib.request.Request(
                f"http://127.0.0.1:{MAIN_PORT}{self.path}",
                data=body,
                method=self.command,
            )
            for key, value in self.headers.items():
                if key.lower() not in ("host", "content-length"):
                    req.add_header(key, value)
            with urllib.request.urlopen(req, timeout=10) as resp:
                self.send_response(resp.status)
                for key, value in resp.getheaders():
                    if key.lower() not in ("transfer-encoding",):
                        self.send_header(key, value)
                self.end_headers()
                self.wfile.write(resp.read())
        except Exception:
            self.send_response(502)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logs


def _run(port):
    server = http.server.HTTPServer(("0.0.0.0", port), ProxyHandler)
    server.serve_forever()


def main():
    ports = set()
    if API_PORT != MAIN_PORT:
        ports.add(API_PORT)
    if MCP_PORT != MAIN_PORT:
        ports.add(MCP_PORT)
    if not ports:
        return
    for port in sorted(ports):
        t = threading.Thread(target=_run, args=(port,), daemon=True)
        t.start()
        print(f"[port-proxy] Listening on {port} → {MAIN_PORT}", file=sys.stderr)
    # Block forever (daemon threads will be killed when main exits)
    threading.Event().wait()


if __name__ == "__main__":
    main()
