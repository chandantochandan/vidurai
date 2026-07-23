# Message Taxonomy (WP-02)

All active IPC messages are classified strictly into one of the following classes:

## Class 1: Persisted Evidence
These events are durably persisted to memories and receive an `event_receipts` entry.
- `file_edit`
- `terminal`
- `diagnostic` (only severe diagnostics meet persistence criteria)

*Stable UUIDv4 event IDs apply exclusively to Class 1 persisted evidence.*

## Class 2: Control and RPC
These requests produce operational side-effects or retrieve data but do not generate `event_receipts`. Their IDs are strictly ephemeral correlation IDs.
- `recall`
- `stats`
- `request`
- `pin`
- `unpin`
- `get_pinned`
- `set_config`
- `resolve_path`
- `context`
- `get_focus`

*Note: Side-effecting operations like `pin` maintain their own separate internal idempotency semantics if applicable.*

## Class 3: Lifecycle and Transient
These represent transient connection states and use transient/correlation IDs. They are strictly excluded from receipt logging.
- `handshake`
- `ping`
- `focus`

## Response-Only Types
These are responses returned by the daemon, never received as inbound requests.
- `ack`
- `error`
- `response`
- `handshake_ack`
- `pong`
- `heartbeat` (server-initiated)

## Internal Evidence Normalization
The future shared normalization and receipt path must handle:
- IPC evidence
- internal smart-file-watcher evidence
- other internal persisted evidence

The smart watcher must create a stable internal UUID at event creation before enqueue. Do not describe all outgoing messages as persisted events.
