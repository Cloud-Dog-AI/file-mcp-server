# Apache-2.0
# Copyright (C) Cloud-Dog, Viewdeck Engineering Ltd.

Place runtime CA certificates in this folder when running with Docker.

Example expected path inside the container:
- `/app/certs/ca.crt`

Recommended run flags:
- `-v $(pwd)/certs:/app/certs:ro`
- `-e FILE_MCP_TLS_CA_BUNDLE=/app/certs/ca.crt`

This enables outbound TLS trust for integrations that require private or corporate CA roots.
