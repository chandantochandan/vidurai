# Processing State Machine (WP-02)

## State Machine Transitions

The lifecycle of an event receipt follows these paths:
```text
recorded → processing → processed
recorded → processing → recorded
recorded → processing → failed
```

## Contract Rules

- Starting an attempt atomically sets `status = 'processing'`, increments `attempt_count`, and sets `last_attempt_at`.
- A recoverable failure returns to `recorded` while attempts remain.
- Maximum attempts: 3.
- At three unsuccessful attempts, transition to `failed`.
- On daemon startup:
  - `processing` with `attempt_count < 3` becomes `recorded`.
  - `processing` with `attempt_count >= 3` becomes `failed`.
- `failed` rows are not automatically retried.
- A same-ID/same-hash resend against `failed` remains a duplicate and must not create another receipt.
- Explicit failed-event recovery is deferred.
