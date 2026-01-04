# Security Policy

**Version:** 2.2.0
**Last Updated:** December 2024

Vidurai is designed with security as a core principle. This document details our security architecture and practices.

## Local-First Architecture

**All data stays on your machine.** Vidurai never sends your code, memories, or context to external servers.

### Data Storage

All data is stored in `~/.vidurai/`:

| File | Purpose | Encryption |
|------|---------|------------|
| `memory.db` | SQLite database (hot storage) | At-rest via OS |
| `vidurai.log` | Daemon logs | None (no sensitive data) |
| `archive/` | Parquet files (cold storage) | At-rest via OS |

### Network Usage

Vidurai makes **zero** network calls for storage. The only network activity is:

1. **MCP Server** (optional): Local HTTP server on `localhost:8765` for Claude Desktop integration
2. **IPC Server**: Unix socket/Named Pipe on `localhost` for VS Code extension

No external APIs are called. No telemetry is collected.

## PII Redaction (Gatekeeper)

All data entering Vidurai passes through the **Gatekeeper**, which redacts sensitive information before storage.

### Redacted Patterns

| Category | Examples | Replacement |
|----------|----------|-------------|
| API Keys | `sk-proj-...`, `AKIA...` | `<REDACTED_API_KEY>` |
| Passwords | `password=secret` | `password=<REDACTED>` |
| Emails | `user@example.com` | `<REDACTED_EMAIL>` |
| IP Addresses | `192.168.1.1` | `<REDACTED_IP>` |
| AWS Credentials | `aws_secret_access_key=...` | `<REDACTED_AWS_KEY>` |
| JWT Tokens | `eyJhbGciOiJIUzI1NiIs...` | `<REDACTED_JWT>` |
| Connection Strings | `postgresql://user:pass@...` | `<REDACTED_CONN_STRING>` |

### Implementation

The Gatekeeper uses 60+ regex patterns to identify and redact sensitive data:

```python
# Example redaction (simplified)
patterns = [
    (r'sk-proj-[A-Za-z0-9]+', '<REDACTED_OPENAI_KEY>'),
    (r'AKIA[A-Z0-9]{16}', '<REDACTED_AWS_ACCESS_KEY>'),
    (r'password\s*[=:]\s*[^\s]+', 'password=<REDACTED>'),
]
```

## Process Isolation

### Daemon (Guardian)

- Runs as a background process under your user account
- No elevated privileges required
- PID tracked in `~/.vidurai/daemon.pid`
- Logs rotated automatically (max 50MB total)

### VS Code Extension

- Runs in VS Code's extension sandbox
- Communicates via Unix socket/Named Pipe (no network)
- Buffers data locally if daemon is unavailable

## Audit Trail

All significant operations are logged:

### Forgetting Ledger

Track what memories were archived or removed:

```bash
vidurai forgetting-log --limit 20
```

Output includes:
- Timestamp
- Action taken (decay, consolidation, aggregation)
- Number of memories affected
- Reason for action
- Whether action is reversible

### Memory Pinning

Critical memories can be pinned to prevent forgetting:

```bash
vidurai pin 123 --reason "Critical security fix"
vidurai pins --show-content
```

### Flight Recorder (Log Rotation)

The daemon uses a rotating log system to prevent disk overflow while maintaining audit history:

```
~/.vidurai/
├── vidurai.log       # Current log (max 10MB)
├── vidurai.log.1     # Previous rotation
├── vidurai.log.2     # Older rotation
├── vidurai.log.3
├── vidurai.log.4
└── vidurai.log.5     # Oldest (auto-deleted)
```

**Configuration:**
- Max file size: 10MB per file
- Backup count: 5 files
- Total max disk: ~50MB for logs
- Encoding: UTF-8

**View logs:**
```bash
vidurai logs -n 50      # Last 50 lines
vidurai logs -f         # Follow in real-time
```

## Threat Model

### In Scope

| Threat | Mitigation |
|--------|------------|
| PII exposure in logs | Gatekeeper redaction |
| Runaway disk usage | Log rotation, archival |
| Stale process lock | PID validation via psutil |
| Data loss on crash | Buffer-to-disk, WAL mode |

### Out of Scope

| Threat | Reason |
|--------|--------|
| Malicious local user | Requires OS-level protection |
| Physical access | Requires disk encryption |
| Memory dumps | Standard process security |

## Reporting Security Issues

If you discover a security vulnerability, please:

1. **Do not** open a public issue
2. Email: security@vidurai.ai (or open a private security advisory on GitHub)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact

We aim to respond within 48 hours and patch critical issues within 7 days.

## Security Checklist for Contributors

When contributing code, ensure:

- [ ] All external input passes through Gatekeeper
- [ ] No hardcoded secrets or credentials
- [ ] No network calls for storage
- [ ] Logging does not expose sensitive data
- [ ] File operations use `Path.home() / ".vidurai"`

---

*Vidurai: Your memories, your machine, your control.*
