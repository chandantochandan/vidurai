# ACK and Error Contract (WP-02)

## Authoritative ACK Mandate

> The daemon returns an ACK only after the raw event receipt has been durably committed.

## Duplicate ACK Matrix

Duplicate ACK must support all receipt states:

```json
{
  "v": 1,
  "type": "ack",
  "id": "event-uuid",
  "ts": 1784654718601,
  "ok": true,
  "data": {
    "status": "duplicate",
    "processing_status": "recorded",
    "memory_id": null
  }
}
```

- `memory_id` is always optional.
- **`recorded`**: duplicate; no new task.
- **`processing`**: duplicate; no parallel processing.
- **`processed`**: duplicate; include `memory_id` where available.
- **`failed`**: duplicate with current error code; no automatic retry. Failed same-hash events are not payload conflicts.

## Error Mappings

The daemon returns `type: "error"` using strict bounded error codes:

- Missing `v` → `missing_required_field` (Non-retryable)
- `v != 1` → `unsupported_version` (Non-retryable)
- Invalid UUID → `malformed_uuid` (Non-retryable)
- Unknown event → `unknown_event_type` (Non-retryable)
- Same ID/different hash → `event_id_payload_conflict` (Non-retryable)
- Durable receipt failure → `internal_durable_write_failure` (Retryable temporary failure)
- Complete invalid JSON line → `malformed_json`, non-retryable for identical bytes.
- Connection closes before a newline-complete frame → no application response; transport retry permitted.
