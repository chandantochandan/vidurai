# Event Payloads (WP-02)

Exact JSON schemas for all Class 1 persisted evidence events.

| Event type | Required data fields | Optional data fields | Persisted | Idempotent | Compatibility notes |
| --- | --- | --- | --- | --- | --- |
| `file_edit` | `project_path`, `file`, `change` | `gist` | Yes | Yes | `change_type` is an active legacy/compatibility alias for `change`. |
| `terminal` | `project_path`, `command`, `output` | `exit_code`, `cwd` | Yes | Yes | `terminal_command` is an active legacy/compatibility alias. |
| `diagnostic` | `project_path`, `file`, `diagnostics` | `source` | Yes (if severe) | Yes | `diagnostics` is an array of `{message, severity}`. `diagnostics` (event type) is a legacy alias for `diagnostic`. |

*Note: `data.project_path` must be preserved. Project UUID, repository identity, producer authentication, and client registration are explicitly deferred to WP-03.*

## Legacy Alias Normalization

Accepted legacy aliases are normalized to canonical field and event names before canonical JSON generation, hashing, storage and downstream processing.

Examples include:
* `change_type` → `change`
* legacy `terminal_command` shape → canonical `terminal`
* legacy `diagnostics` event naming or payload shape → canonical `diagnostic`

Rules:
* normalization occurs before hashing
* canonical and alias representations of the same semantic event must produce the same normalized payload and hash
* the original alias must not create a separate idempotency identity
* normalization must not introduce project UUID, branch identity or producer authentication
