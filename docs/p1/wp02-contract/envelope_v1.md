# Envelope Contract v1 (WP-02)

## Envelope Shape

The frozen `v: 1` envelope for persisted evidence must match the following structure:
```json
{
  "v": 1,
  "type": "file_edit",
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "ts": 1784654718562,
  "data": {
    "project_path": "/Users/chandan/Developer/vidurai",
    "file": "/Users/chandan/Developer/vidurai/src/example.py",
    "gist": "User refactored logic",
    "change": "modify"
  }
}
```

## Contract Rules

- `data.project_path` must be strictly preserved.
- Project UUID, repository identity, producer authentication, and client registration are deferred to WP-03.
- Stable UUIDv4 event IDs (`id`) apply ONLY to Class 1 persisted evidence.
- Class 2 and Class 3 message IDs are purely transient correlation IDs and do not generate receipts.

## Canonical Hashing

The canonical hash is a SHA-256 computed strictly by the daemon. The producer must NOT submit an authoritative payload hash. The input to the canonical hash must:
- Exclude the top-level `id`.
- Include `v`, `type`, `ts`, and the complete `data`.
- Sort object keys recursively.
- Use compact separators (e.g. `":"` and `","` with no spaces).
- Encode as UTF-8.
- Preserve array order.
- Preserve JSON value types.
- Include accepted unknown fields.
- NOT normalize paths before hashing.
- NOT include receipt metadata.
