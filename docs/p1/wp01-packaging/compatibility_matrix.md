# Python Compatibility Matrix

Vidurai enforces strict Python runtime validations. Only versions that pass our extensive installation, API verification, and regression tests are officially supported.

## Validated Matrix

| Python | Build | Install | pip check | Imports | CLI | Daemon | WP-00 | Supported |
|--------|-------|---------|-----------|---------|-----|--------|-------|-----------|
| 3.11   | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | ❌ No |
| 3.12   | PASS  | PASS    | PASS      | PASS    | PASS| PASS   | PASS  | ✅ Yes |
| 3.13   | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | ❌ No |

### Notes
- Python 3.12 is the official minimum baseline because it is the only fully verified target in this development phase.
- Older versions (like 3.11) may technically work based on dependency constraints, but we do not declare them supported until automated CI proves the entire matrix.
