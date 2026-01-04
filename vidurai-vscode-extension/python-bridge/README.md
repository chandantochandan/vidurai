# Vidurai Python Bridge

Python bridge for Vidurai VS Code extension. Handles context tracking and memory management via stdin/stdout communication.

## Architecture
```
VS Code Extension (TypeScript)
 ↓ stdin (JSON events)
Python Bridge (this package)
 ↓ stdout (JSON responses)
VS Code Extension (TypeScript)
```

## Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest test_bridge.py -v
```

## Usage

### Standalone Testing
```bash
# Start bridge
python bridge.py

# Send test event (stdin)
echo '{"type":"ping"}' | python bridge.py

# Expected output (stdout):
# {"status":"ok","message":"pong"}
```

### Event Types

#### 1. Ping
```json
{"type": "ping"}
```

Response:
```json
{"status": "ok", "message": "pong"}
```

#### 2. File Edit
```json
{
 "type": "file_edit",
 "file": "/path/to/file.py",
 "content": "print('hello')"
}
```

Response:
```json
{
 "status": "ok",
 "memory_id": "abc123",
 "salience": "MEDIUM",
 "gist": "Edited file.py",
 "secrets_detected": false
}
```

#### 3. Terminal Output
```json
{
 "type": "terminal_output",
 "command": "pytest",
 "output": "5 passed",
 "exitCode": 0
}
```

#### 4. Diagnostic
```json
{
 "type": "diagnostic",
 "file": "/path/to/file.py",
 "severity": "error",
 "message": "Syntax error"
}
```

#### 5. Recall Context
```json
{
 "type": "recall_context",
 "query": "recent errors",
 "top_k": 10
}
```

#### 6. Get Stats
```json
{"type": "get_stats"}
```

## Configuration

### Session Storage

Sessions are stored in:
- **Windows:** `C:\Users\{username}\.vidurai\sessions\`
- **macOS:** `/Users/{username}/.vidurai/sessions/`
- **Linux:** `/home/{username}/.vidurai/sessions/`

### Secrets Detection

The bridge automatically detects and redacts:
- API keys (OpenAI, Anthropic, GitHub, AWS)
- Passwords
- Database credentials
- Private keys
- JWTs

Files always ignored:
- `.env`, `.env.*`
- `secrets.*`
- `credentials.*`
- `*.key`, `*.pem`

## Testing
```bash
# Run all tests
pytest test_bridge.py -v

# Run with coverage
pytest test_bridge.py --cov=. --cov-report=html
```

## Development

### Using Local Vidurai SDK

If you want to test against the local Vidurai SDK instead of PyPI:

```bash
# From python-bridge directory
pip install -e ../../vidurai
```

This is useful when developing new Vidurai features that the bridge needs to use.

## Requirements

- Python 3.8+
- Vidurai SDK 1.6.1+

## License

MIT
