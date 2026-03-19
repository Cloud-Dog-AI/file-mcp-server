# Audit Events Catalogue

Project: file-mcp-server

| event_type | action | NIST category | Trigger | severity | Example JSON |
|---|---|---|---|---|---|
| auth | token_validate | Authentication | API key or JWT validation on request ingress | INFO | {"event_type":"auth","action":"token_validate","outcome":"success"} |
| user_function | request_execute | Object Access | User/API request execution path | INFO | {"event_type":"user_function","action":"request_execute","outcome":"success"} |
| system_function | dependency_call | System Change | Internal call to DB/MCP/LLM/external service | INFO | {"event_type":"system_function","action":"dependency_call","outcome":"success"} |
| admin_action | config_update | Privileged Use | Runtime configuration or policy change | WARNING | {"event_type":"admin_action","action":"config_update","outcome":"partial"} |
| data_access | read_write | Object Access | Read/write operation against managed data | INFO | {"event_type":"data_access","action":"read_write","outcome":"success"} |
