# VIDURAI P1 WP-02 — CONTRACT PACKAGE INDEX

## Authoritative Contract Documents

This directory contains the frozen, founder-approved contract for WP-02 (Canonical Event Contract and Idempotency). These specifications are authoritative for the implementation of WP-02.

### 1. Message Taxonomy and Schemas
- [Message Taxonomy](message_taxonomy.md) — Categorizes all active IPC messages into Persisted Evidence, Control/RPC, and Lifecycle classes.
- [Event Payloads](event_payloads.md) — Defines exact JSON schemas for all Class 1 persisted evidence events.

### 2. Envelope and Acknowledgement
- [Envelope Contract (v: 1)](envelope_v1.md) — Specifies the backward-compatible transport envelope, canonical hashing, and UUID identity.
- [ACK and Error Contract](ack_and_errors.md) — Defines the synchronous ACKs required before daemon persistence, the duplicate contract, and bounded error codes.

### 3. State and Database
- [Event Receipts SQL Contract](event_receipts_sql.md) — Defines the new `event_receipts` table for idempotency tracking.
- [Processing State Machine](processing_state_machine.md) — Defines the lifecycle of a receipt through `recorded`, `processing`, `processed`, and `failed`.

### 4. Fixtures
- [Compatibility Fixtures](compatibility_fixtures.md) — Explains the duplicate matrix test vectors.
- Raw fixtures are located at `tests/contracts/wp02/` accompanied by `manifest.json`.

---

## Approved Decisions

1. **Transport version**: Remain at `v: 1` (additive fields).
2. **Event Identity**: Producer-generated UUIDv4 required exclusively for Class 1 persisted evidence. Class 2/3 IDs are transient/correlation IDs.
3. **Payload Hash**: Daemon computes SHA-256 over canonical JSON.
4. **Duplicate Behaviour**: Same ID + Same Hash = duplicate success. Same ID + Different Hash = conflict.
5. **Persistence Model**: Use a new additive `event_receipts` table with an auto-generated `receipt_id`. Do not alter `memories`.
6. **ACK Durability boundary**: The daemon returns an ACK only after the raw event receipt has been durably committed.
7. **Derived-memory consistency**: `memories` and `memories_fts` are written atomically.
8. **Legacy missing-ID behaviour**: Temporarily accepted as `legacy_unkeyed` for backward compatibility through P1 beta.

## Deferred WP-03 Decisions

The following identity architectures are strictly deferred and NOT authoritative in WP-02:
- Project UUID and repository identity. Existing `data.project_path` string remains the standard.
- Producer authentication and trusted client identity.
- Client registration.

## Implementation Prerequisites

1. No heavy ML dependencies may be introduced.
2. The SQLite schema must be updated using a proper migration.
3. IPC/WebSocket tests must be updated to inject valid UUIDs.
4. `test_baseline_journey.py` must run successfully on the new contract.
