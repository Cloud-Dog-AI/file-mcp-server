# MCP Server Documentation — File MCP Server

## Transport
Streamable HTTP at `/mcp`

Additional transports: stdio, legacy SSE.

## Authentication
Include API key: `Authorization: Bearer <your-api-key>` or `X-API-Key: <your-api-key>`

Per-profile API keys are also supported via configuration.

## Tools

### File Operations

#### read_file
**Description:** Read a text file.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | File path |
| encoding | string | No | Text encoding |

#### write_file
**Description:** Write text to a file. Supports dry-run mode.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | File path |
| content | string | Yes | Text content to write |
| encoding | string | No | Text encoding |
| dry_run | boolean | No | Preview without writing |

#### delete_file
**Description:** Delete a file. Supports dry-run mode.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | File path |
| dry_run | boolean | No | Preview without deleting |

#### copy_file
**Description:** Copy a file. Supports dry-run mode.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| src | string | Yes | Source path |
| dst | string | Yes | Destination path |
| dry_run | boolean | No | Preview without copying |

#### move_file
**Description:** Move a file or directory. Supports dry-run mode.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| src | string | Yes | Source path |
| dst | string | Yes | Destination path |
| overwrite | boolean | No | Overwrite existing |
| dry_run | boolean | No | Preview without moving |

#### move_path
**Description:** Move a file or directory (alias). Supports dry-run mode.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| src | string | Yes | Source path |
| dst | string | Yes | Destination path |
| overwrite | boolean | No | Overwrite existing |
| dry_run | boolean | No | Preview without moving |

#### rename_path
**Description:** Rename a file or directory. Supports dry-run mode.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | Current path |
| new_name | string | Yes | New name |
| dry_run | boolean | No | Preview without renaming |

#### chmod_path
**Description:** Change file or directory mode. Supports dry-run mode.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | File path |
| mode | string | Yes | Mode (e.g. "0755") |
| dry_run | boolean | No | Preview without changing |

### Directory Operations

#### create_dir
**Description:** Create a directory. Supports dry-run mode.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | Directory path |
| dry_run | boolean | No | Preview without creating |

#### list_dir
**Description:** List directory entries.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | Directory path |

### Search

#### search_paths
**Description:** Search file paths by pattern.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| pattern | string | Yes | Search pattern |
| root | string | No | Root directory |

#### search_content
**Description:** Search file contents by text pattern.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| pattern | string | Yes | Search pattern |
| root | string | No | Root directory |

### Text Utilities

#### diff_text
**Description:** Generate unified diff for text.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| before | string | Yes | Original text |
| after | string | Yes | Modified text |
| context | integer | No | Context lines (default: 3) |

#### b64_encode
**Description:** Encode text as base64.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | Text to encode |
| encoding | string | No | Text encoding |
| urlsafe | boolean | No | Use URL-safe encoding |

#### b64_decode
**Description:** Decode base64 to text.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| data | string | Yes | Base64 data |
| encoding | string | No | Text encoding |
| urlsafe | boolean | No | Use URL-safe decoding |

#### b64_encode_file
**Description:** Encode file contents as base64.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | File path |

#### b64_decode_to_file
**Description:** Decode base64 to file. Supports dry-run mode.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | Destination file path |
| data | string | Yes | Base64 data |
| dry_run | boolean | No | Preview without writing |

### Validation

#### validate_text
**Description:** Validate text content by type (JSON, YAML, etc.).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| content_type | string | Yes | Content type to validate |
| text | string | Yes | Text content |

#### validate_file
**Description:** Validate file content by detected or explicit type.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | File path |

### Structured Editing (JSON)

#### json_get
**Description:** Get JSON value by path.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | JSON text |
| path | string | Yes | JSON path expression |

#### json_set
**Description:** Set JSON value by path.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | JSON text |
| path | string | Yes | JSON path expression |
| value | any | Yes | Value to set |

#### json_delete
**Description:** Delete JSON key by path.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | JSON text |
| path | string | Yes | JSON path expression |

#### json_merge
**Description:** Merge objects into JSON by path.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | JSON text |
| path | string | Yes | JSON path expression |
| value | object | Yes | Object to merge |

#### json_copy
**Description:** Copy a JSON value between paths.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | JSON text |
| src_path | string | Yes | Source path |
| dst_path | string | Yes | Destination path |

#### json_move
**Description:** Move a JSON value between paths.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | JSON text |
| src_path | string | Yes | Source path |
| dst_path | string | Yes | Destination path |

### Structured Editing (YAML)

#### yaml_get
**Description:** Get YAML value by path.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | YAML text |
| path | string | Yes | YAML path expression |

#### yaml_set
**Description:** Set YAML value by path.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | YAML text |
| path | string | Yes | YAML path expression |
| value | any | Yes | Value to set |

#### yaml_delete
**Description:** Delete YAML key by path.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | YAML text |
| path | string | Yes | YAML path expression |

#### yaml_merge
**Description:** Merge objects into YAML by path.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | YAML text |
| path | string | Yes | YAML path expression |
| value | object | Yes | Object to merge |

#### yaml_copy
**Description:** Copy a YAML value between paths.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | YAML text |
| src_path | string | Yes | Source path |
| dst_path | string | Yes | Destination path |

#### yaml_move
**Description:** Move a YAML value between paths.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | YAML text |
| src_path | string | Yes | Source path |
| dst_path | string | Yes | Destination path |

### Structured Editing (XML/HTML/Markdown)

#### xml_set
**Description:** Set XML element value by XPath.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | XML text |
| xpath | string | Yes | XPath expression |
| value | string | Yes | Value to set |

#### html_set
**Description:** Set HTML element value by CSS selector.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | HTML text |
| selector | string | Yes | CSS selector |
| value | string | Yes | Value to set |

#### md_get_section
**Description:** Get a Markdown section by heading.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | Markdown text |
| heading | string | Yes | Section heading |

#### md_set_section
**Description:** Set a Markdown section by heading.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | Markdown text |
| heading | string | Yes | Section heading |
| content | string | Yes | New section content |

#### md_set_frontmatter
**Description:** Set Markdown frontmatter fields.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | Markdown text |
| key | string | Yes | Frontmatter key |
| value | any | Yes | Frontmatter value |

### Line Editing

#### insert_before_line
**Description:** Insert text before a line number.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | Source text |
| line | integer | Yes | Line number |
| content | string | Yes | Content to insert |

#### insert_after_line
**Description:** Insert text after a line number.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | Source text |
| line | integer | Yes | Line number |
| content | string | Yes | Content to insert |

#### replace_line_range
**Description:** Replace a range of lines.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | Source text |
| start | integer | Yes | Start line |
| end | integer | Yes | End line |
| content | string | Yes | Replacement content |

#### replace_regex
**Description:** Replace text matching a regex pattern.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | Source text |
| pattern | string | Yes | Regex pattern |
| replacement | string | Yes | Replacement text |

#### delete_matching_lines
**Description:** Delete lines matching a pattern.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | Source text |
| pattern | string | Yes | Pattern to match |

### Conversion

#### convert_file
**Description:** Convert a file between formats.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | Source file path |
| target_format | string | Yes | Target format |
