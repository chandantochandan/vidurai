# Compatibility Fixtures (WP-02)

The fixtures defined in `tests/contracts/wp02/` accompanied by `manifest.json` provide the static test vectors required to implement and verify the WP-02 IPC and Idempotency contract.

## Duplicate Matrix Tests
Static fixture manifest metadata defines the receipt-state preconditions for evaluating duplicate behaviour across the `recorded`, `processing`, `processed`, and `failed` states.

## Fixture Constraints
- Must use numeric `"v": 1`.
- Must match documented payload fields exactly (`file_edit` uses `project_path`, `file`, `change`, `gist`).
- Must use only error/status codes defined by `ack_and_errors.md` (no arbitrary `ERR_*` codes).
- RPC and lifecycle fixtures must set `receipt_expected: false`.
- Unknown extra fields must be accepted, preserved, and included in hashing.
- `oversized_payload` is explicitly removed as size limits are deferred.
- Every fixture includes a deterministic, pre-computed canonical SHA-256 hash.
