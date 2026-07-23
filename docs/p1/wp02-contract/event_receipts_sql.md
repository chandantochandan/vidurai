# Event Receipts SQL Contract (WP-02)

## Schema Freeze

The exact schema for the `event_receipts` table is frozen as follows:

```sql
CREATE TABLE event_receipts (
    receipt_id TEXT PRIMARY KEY NOT NULL,
    event_id TEXT,
    event_type TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL
        CHECK (status IN ('recorded', 'processing', 'processed', 'failed')),
    memory_id INTEGER,
    received_at INTEGER NOT NULL,
    processed_at INTEGER,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_attempt_at INTEGER,
    error_code TEXT
);

CREATE UNIQUE INDEX idx_event_receipts_event_id
ON event_receipts(event_id)
WHERE event_id IS NOT NULL;

CREATE INDEX idx_event_receipts_recovery
ON event_receipts(status, received_at);
```

### Contract Rules
- Every receipt gets an internal daemon-generated UUIDv4 `receipt_id`.
- Producer `event_id` is nullable only for `legacy_unkeyed` compatibility.
- Legacy receipts are durable but not idempotent.
- Do not rely on nullable SQLite primary-key quirks.
- Do not add idempotency columns to `memories`.
- Do not require a foreign key to `memories` in WP-02.
- Receipt retention policy remains documented as a later operational decision.

## Payload JSON Storage

`payload_json` stores the canonical compact JSON text used as the SHA-256 hash input.

The stored representation must:
- exclude top-level `id`
- include numeric `v`
- include `type`
- include producer capture timestamp `ts`
- include complete normalized `data`
- preserve accepted unknown fields inside `data`
- recursively sort object keys
- use compact JSON separators
- use UTF-8
- preserve array order
- preserve JSON value types
- preserve path strings exactly
- exclude receipt metadata

The text stored in SQLite must be the compact deterministic representation, not the original whitespace-preserving transport string.
## Transaction Boundary Freeze

The required transaction boundary for processing an event into a memory must strictly be:

```text
BEGIN
INSERT memories
INSERT memories_fts
UPDATE event_receipts
COMMIT
```

Any memory or FTS failure rolls back the entire transaction.
